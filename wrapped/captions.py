"""One-line captions for each award and a bio line for each profile.

The default is a template, written from the computed fields. With ``--claude``
the lines are written by Claude, but only from those same computed fields
(title, winner, value text, the receipt and its date; for a bio: name, message
count, peak hour, award titles, top emoji). Nothing else is sent: no other
messages, and nobody who didn't opt in (their names are already "someone" in
the receipts). A caption that states a number not in its own fields is
replaced by the template, so the model can't add a fact. Any error, refusal or
missing key means templates for everything.

The API key is read from the macOS Keychain (service ``anthropic-api-key``,
account ``hercules``) into this process's memory only and handed straight to
the client. It is never printed, logged, put in argv or in the environment.
"""

from __future__ import annotations

import json
import re
import subprocess

try:  # optional: templates work without the SDK
    import anthropic
except ImportError:  # pragma: no cover - depends on the environment
    anthropic = None

MODEL = "claude-opus-5-5"
KEYCHAIN_SERVICE = "anthropic-api-key"
KEYCHAIN_ACCOUNT = "hercules"
MAX_CAPTION = 140

TEMPLATES = {
    "main_character": "{winner} carried this chat. {value}.",
    "novelist": "{winner} doesn't text, {winner} publishes.",
    "three_am": "{winner} does their best thinking when everyone else is asleep.",
    "omw": "{winner} {value}. The group is still waiting.",
    "left_on_read": "{winner} kept asking. The chat kept not answering.",
    "hype": "{winner} has one volume setting, and it's this one.",
    "speed_demon": "{winner} replies before you've finished the thought.",
    "ghost": "{winner} said little, and made it count.",
    "emoji": "One emoji ruled the semester, and {winner} is its biggest fan.",
    "group_word": "Every group has a word. {winner} made sure this was yours.",
    "busiest_day": "The day the chat lost it, and {winner} started it.",
}

CAPTION_SYSTEM = """\
You write one short, warm, funny caption per award for a "Wrapped" story of a college group chat.

Rules:
- Use only the facts in the award you are given: its title, winner, value text and the quoted receipt. Never add a number, name, date, place or event that isn't in those fields.
- One sentence, at most 120 characters. No hashtags, no emoji unless the award's own fields contain one.
- Tease kindly. Never mock looks, identity, grades, health or anything outside the chat.
- "someone" stands for a person who did not opt in; never guess who it is.
Return JSON matching the schema, one entry per award key, and one bio per member."""

BIO_TEMPLATE = "{messages} messages, mostly around {peak}. {awards}"

CAPTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["captions", "bios"],
    "properties": {
        "captions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["key", "caption"],
                "properties": {"key": {"type": "string"}, "caption": {"type": "string"}},
            },
        },
        "bios": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "bio"],
                "properties": {"name": {"type": "string"}, "bio": {"type": "string"}},
            },
        },
    },
}


# ------------------------------------------------------------ templates ---

def _short_value(value_text: str) -> str:
    return value_text.split(";")[0].split(", ")[0]


def template_caption(award: dict) -> str:
    t = TEMPLATES.get(award["key"], "{winner}: {title}.")
    return t.format(winner=award["winner"], value=_short_value(award["value_text"]), title=award["title"])


def template_bio(profile: dict) -> str:
    titles = [a["title"] for a in profile["awards"]]
    if titles:
        awards = "Holder of " + (", ".join(titles[:-1]) + " and " + titles[-1] if len(titles) > 1 else titles[0]) + "."
    else:
        awards = "Here for the chat, not the trophies."
    peak = profile["peak_hour"] or "all hours"
    return BIO_TEMPLATE.format(messages=f"{profile['messages']:,}", peak=peak, awards=awards)


def templates(awards: list[dict], profiles: list[dict]) -> dict:
    return {
        "source": "template",
        "awards": {a["key"]: template_caption(a) for a in awards},
        "bios": {p["name"]: template_bio(p) for p in profiles},
    }


# ---------------------------------------------------------------- Claude ---

def award_facts(award: dict) -> dict:
    """Exactly what the model may see for one award."""
    return {
        "key": award["key"],
        "title": award["title"],
        "winner": award["winner"],
        "value_text": award["value_text"],
        "receipt": {"text": award["receipt"]["text"], "date": award["receipt"]["ts"][:10]},
    }


def profile_facts(profile: dict) -> dict:
    """Exactly what the model may see for one bio."""
    return {
        "name": profile["name"],
        "messages": profile["messages"],
        "peak_hour": profile["peak_hour"],
        "awards": [a["title"] for a in profile["awards"]],
        "top_emoji": [e["emoji"] for e in profile["top_emoji"]],
    }


def request_payload(awards: list[dict], profiles: list[dict]) -> str:
    return json.dumps(
        {"awards": [award_facts(a) for a in awards], "members": [profile_facts(p) for p in profiles]},
        ensure_ascii=False,
    )


_NUM = re.compile(r"\d+")


def _grounded(line: str, facts: dict) -> bool:
    """Every digit run in ``line`` appears in the facts it was written from."""
    allowed = set(_NUM.findall(json.dumps(facts, ensure_ascii=False).replace(",", "")))
    return all(n in allowed for n in _NUM.findall(line.replace(",", "")))


def _clean(line) -> str | None:
    if not isinstance(line, str):
        return None
    line = " ".join(line.split())
    return line if 0 < len(line) <= MAX_CAPTION else None


def claude_captions(awards: list[dict], profiles: list[dict], client) -> dict:
    """Claude's lines where they pass the checks, templates everywhere else."""
    out = templates(awards, profiles)
    if not awards and not profiles:
        return out
    try:
        resp = client.beta.messages.create(
            model=MODEL,
            max_tokens=4000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": CAPTION_SCHEMA}},
            system=CAPTION_SYSTEM,
            messages=[{"role": "user", "content": request_payload(awards, profiles)}],
        )
        if resp.stop_reason in ("refusal", "max_tokens"):
            return out
        body = next(block.text for block in resp.content if getattr(block, "type", None) == "text")
        data = json.loads(body)
    except Exception:  # noqa: BLE001 - every failure means "use the templates", by design
        return out

    by_key = {a["key"]: a for a in awards}
    by_name = {p["name"]: p for p in profiles}
    used = 0
    for item in data.get("captions") or []:
        award = by_key.get(item.get("key"))
        line = _clean(item.get("caption"))
        if award and line and _grounded(line, award_facts(award)):
            out["awards"][award["key"]] = line
            used += 1
    for item in data.get("bios") or []:
        profile = by_name.get(item.get("name"))
        line = _clean(item.get("bio"))
        if profile and line and _grounded(line, profile_facts(profile)):
            out["bios"][profile["name"]] = line
            used += 1
    if used:
        out["source"] = "claude"
    return out


def read_key() -> str | None:
    """The key from the Keychain, or None. Never printed or stored anywhere."""
    try:
        proc = subprocess.run(
            ["security", "find-generic-password", "-a", KEYCHAIN_ACCOUNT, "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return (proc.stdout.strip() or None) if proc.returncode == 0 else None


def make_client():
    """An Anthropic client holding the Keychain key, or None (no SDK or no key)."""
    if anthropic is None:
        return None
    key = read_key()
    if key is None:
        return None
    return anthropic.Anthropic(api_key=key)


def captions(awards: list[dict], profiles: list[dict], client=None) -> dict:
    return claude_captions(awards, profiles, client) if client is not None else templates(awards, profiles)
