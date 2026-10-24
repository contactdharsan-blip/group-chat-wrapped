"""Per-person profiles for the web app, for opted-in members only.

``build(messages, result)`` takes the messages and the ``stats.compute`` result
and returns one profile per name in ``result["members"]``. Nobody else gets a
profile, and their names are kept out of every field: top words skip every
author's name, and posts are the already-redacted award receipts.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter

from .model import Message
from .stats import CHAT_SLANG, EMOJI, STOPWORDS, fmt_hour, words

TOP_WORDS = 5
TOP_EMOJI = 3


def handle(name: str) -> str:
    return "@" + (re.sub(r"[^\w]", "", name.casefold().replace(" ", "_")) or "member")


def initials(name: str) -> str:
    parts = [p for p in re.split(r"\s+", name.strip()) if p]
    return "".join(p[0] for p in parts[:2]).upper() or "?"


def hue(name: str) -> int:
    """A stable hue for the avatar gradient, so a person keeps their colour across runs."""
    return int(hashlib.sha256(name.encode("utf-8")).hexdigest()[:6], 16) % 360


def _reactions(by_key: dict, receipt: dict) -> dict[str, int]:
    m = by_key.get((receipt["author"], receipt["ts"]))
    return dict(sorted(m.reactions.items(), key=lambda kv: (-kv[1], kv[0]))) if m and m.reactions else {}


def build(messages: list[Message], result: dict) -> list[dict]:
    members = list(result["members"])
    name_tokens = {t for m in messages for t in words(m.author)}
    by_key = {(m.author, m.ts.isoformat()): m for m in messages}
    mine: dict[str, list[Message]] = {name: [] for name in members}
    for m in messages:
        if m.author in mine:
            mine[m.author].append(m)

    profiles = []
    for name in members:
        msgs = mine[name]
        hours = Counter(m.ts.hour for m in msgs)
        peak = min(hours, key=lambda h: (-hours[h], h)) if hours else None
        emoji = Counter(e for m in msgs for e in EMOJI.findall(m.text))
        vocab = Counter(
            w for m in msgs for w in words(m.text)
            if len(w) >= 3 and w not in STOPWORDS and w not in CHAT_SLANG and w not in name_tokens and "'" not in w
        )
        awards, posts = [], []
        for a in result["awards"]:
            if a["winner"] == name:
                awards.append({"key": a["key"], "title": a["title"]})
            for role in ("context", "receipt"):
                r = a.get(role)
                if r and r["author"] == name:
                    posts.append({
                        "award_key": a["key"],
                        "award_title": a["title"],
                        "text": r["text"],
                        "ts": r["ts"],
                        "reactions": _reactions(by_key, r),
                    })
        profiles.append({
            "name": name,
            "handle": handle(name),
            "initials": initials(name),
            "hue": hue(name),
            "messages": len(msgs),
            "posts": len(posts),
            "awards": awards,
            "peak_hour": fmt_hour(peak) if peak is not None else None,
            "top_emoji": [{"emoji": e, "count": n} for e, n in sorted(emoji.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_EMOJI]],
            "top_words": [{"word": w, "count": n} for w, n in sorted(vocab.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_WORDS]],
            "receipts": posts,
        })
    return profiles
