"""Turn a chat export into a list of Message, oldest first.

Supported:
  * WhatsApp .txt exports, iOS style   ``[10/24/26, 9:41:03 PM] Name: text``
    and Android style                  ``10/24/26, 21:41 - Name: text``
  * Discord channel JSON in the DiscordChatExporter shape
  * CSV with a ``timestamp,author,text`` header
"""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime
from pathlib import Path

from .model import Message

# Invisible marks WhatsApp sprinkles into exports: narrow no-break space before
# AM/PM, no-break space, left-to-right mark, BOM.
_INVISIBLES = str.maketrans({" ": " ", " ": " ", "‎": None, "‏": None, "﻿": None})

_IOS = re.compile(
    r"^\[(?P<date>\d{1,4}[./-]\d{1,2}[./-]\d{1,4}),? (?P<time>\d{1,2}[:.]\d{2}(?:[:.]\d{2})?(?: ?[AaPp]\.? ?[Mm]\.?)?)\] (?P<rest>.*)$"
)
_ANDROID = re.compile(
    r"^(?P<date>\d{1,4}[./-]\d{1,2}[./-]\d{1,4}),? (?P<time>\d{1,2}[:.]\d{2}(?:[:.]\d{2})?(?: ?[AaPp]\.? ?[Mm]\.?)?) [-–] (?P<rest>.*)$"
)
# Media placeholders: Android "<Media omitted>", iOS "image omitted", "sticker omitted"...
_MEDIA = re.compile(
    r"^(<Media omitted>|<attached: [^>]*>|(image|video|audio|sticker|GIF|document|Contact card) omitted|.*\bdocument omitted)$",
    re.IGNORECASE,
)
_SYSTEM_BODY = re.compile(r"^Messages and calls are end-to-end encrypted", re.IGNORECASE)
_LRM = "\u200e"


def _parse_wa_datetime(date: str, time: str, day_first: bool) -> datetime:
    a, b, c = (int(x) for x in re.split(r"[./-]", date))
    if a > 31:  # year-first, e.g. 2026-10-24
        year, month, day = a, b, c
    elif day_first:
        day, month, year = a, b, c
    else:
        month, day, year = a, b, c
    if year < 100:
        year += 2000
    t = time.replace(".", ":").upper().replace(" ", "")
    ampm = None
    if t.endswith("AM") or t.endswith("PM"):
        ampm, t = t[-2:], t[:-2]
    parts = [int(x) for x in t.split(":")]
    hour, minute = parts[0], parts[1]
    second = parts[2] if len(parts) > 2 else 0
    if ampm == "AM" and hour == 12:
        hour = 0
    elif ampm == "PM" and hour != 12:
        hour += 12
    return datetime(year, month, day, hour, minute, second)


def _match_header(line: str):
    return _IOS.match(line) or _ANDROID.match(line)


def parse_whatsapp(text: str) -> list[Message]:
    # iOS marks system notices (written with the group's name as author) by
    # starting the body with a left-to-right mark; remember that before the
    # invisibles are stripped.
    lines = [line.replace(f": {_LRM}", ": \x00", 1).translate(_INVISIBLES) for line in text.splitlines()]
    headers = [m for m in map(_match_header, lines) if m]
    # Month-first unless some first field can only be a day (> 12).
    day_first = any(
        12 < int(re.split(r"[./-]", m["date"])[0]) <= 31 for m in headers
    )

    messages: list[Message] = []
    current: Message | None = None
    for line in lines:
        m = _match_header(line)
        if not m:
            if current is not None:  # continuation of a multi-line message
                current.text = f"{current.text}\n{line}" if current.text else line
            continue
        ts = _parse_wa_datetime(m["date"], m["time"], day_first)
        rest = m["rest"]
        if ": " not in rest:
            # System line: "Messages and calls are end-to-end encrypted...",
            # "Maya created group", "Theo added Jordan", ...
            current = None
            continue
        author, body = rest.split(": ", 1)
        marked = body.startswith("\x00")
        body = body.lstrip("\x00").strip()
        if _MEDIA.match(body):
            current = Message(ts=ts, author=author.strip(), text="", attachments=1)
        elif marked or _SYSTEM_BODY.match(body) or body in ("This message was deleted", "You deleted this message", "Missed voice call", "Missed video call"):
            current = None
            continue
        else:
            current = Message(ts=ts, author=author.strip(), text=body)
        messages.append(current)
    return _sorted(messages)


def _naive_wall_clock(stamp: str) -> datetime:
    # Keep the wall-clock time the exporter wrote (it uses the exporter's local
    # offset), so "3 AM" means 3 AM for the people in the chat.
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).replace(tzinfo=None)


def parse_discord(text: str) -> list[Message]:
    data = json.loads(text)
    messages = []
    for raw in data.get("messages", []):
        if raw.get("type") not in (None, "Default", "Reply"):
            continue  # joins, pins, thread notices
        author = raw.get("author") or {}
        name = author.get("nickname") or author.get("name") or "unknown"
        ref = raw.get("reference") or {}
        reactions = {}
        for r in raw.get("reactions") or []:
            emoji = (r.get("emoji") or {}).get("name")
            if emoji:
                reactions[emoji] = reactions.get(emoji, 0) + int(r.get("count", 0))
        messages.append(
            Message(
                ts=_naive_wall_clock(raw["timestamp"]),
                author=name,
                text=raw.get("content") or "",
                reply_to=ref.get("messageId"),
                reactions=reactions,
                attachments=len(raw.get("attachments") or []),
            )
        )
    return _sorted(messages)


def parse_csv(text: str) -> list[Message]:
    reader = csv.DictReader(io.StringIO(text, newline=""))
    return _sorted(
        Message(ts=_naive_wall_clock(row["timestamp"].strip()), author=row["author"].strip(), text=row["text"])
        for row in reader
        if row.get("timestamp") and row.get("author")
    )


def _sorted(messages) -> list[Message]:
    # Stable: messages with equal timestamps keep export order.
    return sorted(messages, key=lambda m: m.ts)


PARSERS = {"whatsapp": parse_whatsapp, "discord": parse_discord, "csv": parse_csv}


def load(path: str | Path, fmt: str) -> list[Message]:
    if fmt not in PARSERS:
        raise ValueError(f"unknown format {fmt!r}; expected one of {', '.join(PARSERS)}")
    return PARSERS[fmt](Path(path).read_text(encoding="utf-8-sig"))
