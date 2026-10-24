"""What the web app's API returns, built with the standard library only.

``wrapped/server.py`` is a thin FastAPI layer over these functions, and
``python3 -m wrapped.webapi --dump-demo web/dist/demo.json`` bakes the demo
response for the static (no-server) build. Uploaded bytes are parsed in
memory and never written anywhere.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from . import captions, importers, profiles, stats
from .model import Message

MAX_BYTES = 20 * 1024 * 1024
FORMATS = ("auto", "whatsapp", "discord", "csv", "instagram")
ROOT = Path(__file__).resolve().parent.parent
DEMO_CHAT = ROOT / "demo" / "demo-chat.txt"
DEMO_NAME = "Floor 4 Survivors"
DEMO_OPTIN = ("Maya", "Jordan", "Priya", "Theo")


class UploadError(ValueError):
    """A message safe to show the user; it never quotes the upload."""


def detect_format(text: str) -> str:
    head = text.lstrip()[:4000]
    if head.startswith("{"):
        if '"sender_name"' in head or '"participants"' in head or '"timestamp_ms"' in head:
            return "instagram"
        return "discord"
    first = head.splitlines()[0].lower() if head else ""
    if "timestamp" in first and "author" in first and "," in first:
        return "csv"
    return "whatsapp"


def parse_upload(data: bytes, fmt: str = "auto") -> tuple[list[Message], str]:
    if len(data) > MAX_BYTES:
        raise UploadError(f"That file is over {MAX_BYTES // (1024 * 1024)} MB. Export without media and try again.")
    if fmt not in FORMATS:
        raise UploadError(f"Unknown format. Use one of: {', '.join(FORMATS)}.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise UploadError("That file isn't text. Upload the .txt, .json or .csv export itself.") from None
    if fmt == "auto":
        fmt = detect_format(text)
    try:
        messages = importers.PARSERS[fmt](text)
    except Exception:  # noqa: BLE001 - any parser failure is "couldn't read it", without echoing content
        raise UploadError(f"Couldn't read that as a {fmt} export. Check the format and try again.") from None
    if not messages:
        raise UploadError(f"No messages found reading it as a {fmt} export.")
    return messages, fmt


def members_payload(messages: list[Message], fmt: str) -> dict:
    counts = Counter(m.author for m in messages)
    return {
        "format": fmt,
        "messages": len(messages),
        "members": [{"name": n, "messages": c} for n, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].casefold()))],
    }


def _group_page(result: dict, chat_name: str, people: list[dict]) -> dict:
    g = result["group"]
    by_key = {a["key"]: a for a in result["awards"]}
    return {
        "name": chat_name,
        "members": [{k: p[k] for k in ("name", "handle", "initials", "hue")} for p in people],
        "others": max(0, g.get("people", 0) - len(people)),
        "busiest_day": by_key.get("busiest_day"),
        "group_word": by_key.get("group_word"),
    }


def wrapped_payload(messages: list[Message], optin, chat_name: str = "Group Chat Wrapped", client=None) -> dict:
    result = stats.compute(messages, {n for n in optin if n.strip()})
    people = profiles.build(messages, result)
    caps = captions.captions(result["awards"], people, client)
    return {
        "chat_name": chat_name,
        "result": result,
        "profiles": people,
        "group": _group_page(result, chat_name, people),
        "captions": caps,
    }


def demo_payload(client=None) -> dict:
    messages = importers.parse_whatsapp(DEMO_CHAT.read_text(encoding="utf-8-sig"))
    return wrapped_payload(messages, DEMO_OPTIN, DEMO_NAME, client) | {"demo": True}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wrapped.webapi")
    p.add_argument("--dump-demo", metavar="PATH", required=True, help="write the /api/demo response to PATH")
    args = p.parse_args(argv)
    out = Path(args.dump_demo)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(demo_payload(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"demo -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
