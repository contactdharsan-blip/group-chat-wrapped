"""The iMessage bridge (macOS): one group chat, read from chat.db, answered through Messages.

    python3 -m wrapped.platforms.imessage --list-chats
    python3 -m wrapped.platforms.imessage --chat-guid "any;+;chat123..." [--names names.json] [--me "Dharsan"] [--dry-run]

Members type "wrapped optin", "wrapped optout" or "wrapped" in the group. The
bridge polls chat.db (opened read-only) every few seconds for rows after the
last one it saw. On "wrapped" it runs the pipeline and sends a short text, then
the slides, into that same group.

Safety: a Sender is built for one group chat id and has no way to address any
other; the Bridge refuses a Sender built for a different chat; and a chat id
that isn't a group (";+;") is refused outright.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .. import render
from ..model import Message
from . import config_dir, make_story

DEFAULT_DB = Path.home() / "Library" / "Messages" / "chat.db"
DEFAULT_STAGE = Path.home() / "Pictures" / "group-chat-wrapped"
APPLE_EPOCH = 978307200  # 2001-01-01 UTC in Unix seconds
POLL_SECONDS = 3.0
COOLDOWN_SECONDS = 600  # one Wrapped per chat per ten minutes, however often it's asked for
GROUP_STYLE = 43
_GROUP_GUID = re.compile(r"[^;]+;\+;.+")
# Zero-width space/non-joiner/joiner, word joiner, BOM; and U+FFFC, the
# object-replacement character Messages puts where an attachment sat.
_INVISIBLES = re.compile("[​-‍⁠﻿￼]")
TAPBACKS = {2000: "❤️", 2001: "👍", 2002: "👎", 2003: "😂", 2004: "‼️", 2005: "❓"}
COMMANDS = {"wrapped optin": "optin", "wrapped optout": "optout", "wrapped": "run"}


# ---------- reading chat.db ----------

def decode_attributed_body(blob: bytes | None) -> str | None:
    """The NSString inside an attributedBody typedstream, or None.

    The layout is ``...NSString\\x01\\x94\\x84\\x01+<length><utf-8 bytes>...``.
    The length is one byte, or 0x81 then a little-endian uint16, or 0x82 then
    a little-endian uint32."""
    if not blob:
        return None
    blob = bytes(blob)
    i = blob.find(b"NSString")
    if i < 0:
        return None
    j = blob.find(b"\x01+", i + len(b"NSString"))
    if j < 0 or j - i > 16:
        return None
    p = j + 2
    if p >= len(blob):
        return None
    tag = blob[p]
    if tag == 0x81:
        size, p = int.from_bytes(blob[p + 1:p + 3], "little"), p + 3
    elif tag == 0x82:
        size, p = int.from_bytes(blob[p + 1:p + 5], "little"), p + 5
    elif tag < 0x80:
        size, p = tag, p + 1
    else:
        return None
    raw = blob[p:p + size]
    if len(raw) != size:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def clean(text: str | None) -> str:
    return _INVISIBLES.sub("", text or "").strip()


def apple_time(value: int | float) -> datetime:
    """message.date as a naive local wall clock. Nanoseconds since 2001 on
    macOS 10.13 and later; plain seconds before that."""
    seconds = value / 1e9 if abs(value) > 1e11 else value
    return datetime.fromtimestamp(seconds + APPLE_EPOCH)


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(db_path).expanduser().resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def list_chats(conn: sqlite3.Connection) -> list[dict]:
    """Group chats with their guid, name, size and last activity. No message text."""
    rows = conn.execute(
        """
        SELECT c.guid, c.display_name,
               (SELECT COUNT(*) FROM chat_handle_join ch WHERE ch.chat_id = c.ROWID) AS others,
               (SELECT MAX(m.date) FROM chat_message_join j JOIN message m ON m.ROWID = j.message_id
                 WHERE j.chat_id = c.ROWID) AS last_date
          FROM chat c
         WHERE c.style = ? OR c.guid LIKE '%;+;%'
         ORDER BY last_date IS NULL, last_date DESC
        """,
        (GROUP_STYLE,),
    ).fetchall()
    return [
        {
            "guid": r["guid"],
            "name": r["display_name"] or "",
            "people": r["others"] + 1,  # the handles, plus you
            "last": apple_time(r["last_date"]) if r["last_date"] is not None else None,
        }
        for r in rows
    ]


def chat_rowid(conn: sqlite3.Connection, guid: str) -> int | None:
    row = conn.execute("SELECT ROWID FROM chat WHERE guid = ?", (guid,)).fetchone()
    return row[0] if row else None


@dataclass
class Row:
    rowid: int
    guid: str
    text: str
    sender: str  # "me" or the handle id (phone number or email)
    ts: datetime
    attachments: int
    tapback: int  # associated_message_type: 0 for a normal message
    target: str | None  # the message a tapback is on
    reply_to: str | None
    is_event: bool  # renames, people added or removed...


def fetch_rows(conn: sqlite3.Connection, chat_id: int, after: int = 0) -> list[Row]:
    rows = conn.execute(
        """
        SELECT m.ROWID AS rowid, m.guid, m.text, m.attributedBody, m.is_from_me, h.id AS handle, m.date,
               m.cache_has_attachments, m.associated_message_type, m.associated_message_guid,
               m.thread_originator_guid, m.item_type
          FROM chat_message_join j
          JOIN message m ON m.ROWID = j.message_id
          LEFT JOIN handle h ON h.ROWID = m.handle_id
         WHERE j.chat_id = ? AND m.ROWID > ?
         ORDER BY m.ROWID
        """,
        (chat_id, after),
    ).fetchall()
    out = []
    for r in rows:
        text = r["text"] if r["text"] is not None else decode_attributed_body(r["attributedBody"])
        target = r["associated_message_guid"]
        if target:  # "p:0/<guid>" or "bp:<guid>"
            target = target.rsplit("/", 1)[-1].split(":", 1)[-1]
        out.append(Row(
            rowid=r["rowid"], guid=r["guid"], text=clean(text),
            sender="me" if r["is_from_me"] else (r["handle"] or "unknown"),
            ts=apple_time(r["date"]), attachments=1 if r["cache_has_attachments"] else 0,
            tapback=r["associated_message_type"] or 0, target=target,
            reply_to=r["thread_originator_guid"], is_event=bool(r["item_type"]),
        ))
    return out


class Names:
    """Sender key ("me" or a handle) to display name."""

    def __init__(self, mapping: dict[str, str] | None = None, me: str = "Me"):
        self.mapping, self.me = dict(mapping or {}), me

    def __call__(self, sender: str) -> str:
        return self.me if sender == "me" else self.mapping.get(sender, sender)

    def known(self, sender: str) -> bool:
        return sender == "me" or sender in self.mapping


def parse_command(text: str) -> str | None:
    return COMMANDS.get(" ".join(text.split()).casefold())


def to_messages(rows: list[Row], names: Names) -> list[Message]:
    """Normal messages, with tapbacks counted on their targets. Commands, group
    events and removed tapbacks are left out."""
    by_guid: dict[str, Message] = {}
    messages: list[Message] = []
    for r in rows:
        if r.is_event:
            continue
        if r.tapback:
            target = by_guid.get(r.target or "")
            emoji = TAPBACKS.get(r.tapback)
            if target is not None and emoji:
                target.reactions[emoji] = target.reactions.get(emoji, 0) + 1
            continue
        if parse_command(r.text):
            continue
        if not r.text and not r.attachments:
            continue
        m = Message(ts=r.ts, author=names(r.sender), text=r.text, reply_to=r.reply_to, attachments=r.attachments)
        by_guid[r.guid] = m
        messages.append(m)
    return sorted(messages, key=lambda m: m.ts)


# ---------- sending ----------

_SEND_TEXT = [
    "on run argv",
    'tell application "Messages" to send (item 1 of argv) to chat id (item 2 of argv)',
    "end run",
]
_SEND_FILE = [
    "on run argv",
    "set f to POSIX file (item 1 of argv)",
    'tell application "Messages" to send f to chat id (item 2 of argv)',
    "end run",
]


def is_group_guid(guid: str) -> bool:
    return bool(_GROUP_GUID.fullmatch(guid or ""))


class Sender:
    """Sends into exactly one group chat, fixed at construction. There is no
    parameter for a target: nothing reachable from here can address another
    chat or a person. The chat id and the text or path reach osascript as
    arguments (``on run argv``), never pasted into the script."""

    def __init__(self, chat_guid: str, dry_run: bool = True, stage_dir: Path = DEFAULT_STAGE,
                 run=subprocess.run, echo=print):
        if not is_group_guid(chat_guid):
            raise ValueError(f"refusing {chat_guid!r}: the bridge only sends to a group chat (an id with ';+;')")
        self.chat_guid, self.dry_run, self.stage_dir, self._run, self._echo = chat_guid, dry_run, Path(stage_dir), run, echo

    def _osascript(self, script: list[str], arg: str) -> None:
        cmd = ["osascript"]
        for line in script:
            cmd += ["-e", line]
        cmd += [arg, self.chat_guid]
        proc = self._run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            raise RuntimeError(f"Messages refused the send: {proc.stderr.strip()}")

    def send_text(self, text: str) -> None:
        if self.dry_run:
            self._echo(f"[dry run] would send to {self.chat_guid}: {text}")
            return
        self._osascript(_SEND_TEXT, text)

    def send_file(self, path: Path) -> None:
        if self.dry_run:
            self._echo(f"[dry run] would send to {self.chat_guid}: file {path}")
            return
        # Messages can't always read files from arbitrary folders, and it
        # uploads after the script returns, so send a copy that stays put.
        self.stage_dir.mkdir(parents=True, exist_ok=True)
        staged = self.stage_dir / f"{int(time.time())}-{Path(path).name}"
        shutil.copy2(path, staged)
        self._osascript(_SEND_FILE, str(staged))


# ---------- the bridge ----------

class Bridge:
    def __init__(self, chat_guid: str, sender: Sender, names: Names, *, db_path: Path = DEFAULT_DB,
                 state_path: Path | None = None, out_dir: Path | None = None, render_media: bool = True,
                 story_maker=make_story, clock=time.time, echo=print):
        if sender.chat_guid != chat_guid:
            raise ValueError("the sender is bound to a different chat than the bridge")
        self.chat_guid, self.sender, self.names, self.db_path = chat_guid, sender, names, Path(db_path)
        digest = hashlib.sha256(chat_guid.encode()).hexdigest()[:12]
        self.state_path = Path(state_path) if state_path else config_dir() / f"imessage-{digest}.json"
        self.out_dir, self.render_media, self.story_maker = out_dir, render_media, story_maker
        self.clock, self.echo = clock, echo
        self.last_run = None

    # state: {"last_rowid": int, "optins": [sender keys]}
    def load_state(self) -> dict:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}

    def save_state(self, state: dict) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, self.state_path)

    def _chat_id(self, conn) -> int:
        chat_id = chat_rowid(conn, self.chat_guid)
        if chat_id is None:
            raise SystemExit(f"no chat with id {self.chat_guid!r} in {self.db_path} (try --list-chats)")
        return chat_id

    def start(self) -> dict:
        """Load state; on the first start, begin after the newest row so old commands don't fire."""
        state = self.load_state()
        if "last_rowid" not in state:
            with closing(connect(self.db_path)) as conn:
                rows = fetch_rows(conn, self._chat_id(conn))
            state = {"last_rowid": rows[-1].rowid if rows else 0, "optins": state.get("optins", [])}
            self.save_state(state)
        return state

    def poll_once(self) -> list[str]:
        """Handle the commands posted since the last poll. Returns what was done."""
        state = self.start()
        with closing(connect(self.db_path)) as conn:
            rows = fetch_rows(conn, self._chat_id(conn), state["last_rowid"])
        done, want_run = [], False
        optins = list(state.get("optins", []))
        for r in rows:
            cmd = None if (r.tapback or r.is_event) else parse_command(r.text)
            if cmd == "optin" and r.sender not in optins:
                optins.append(r.sender)
                done.append(f"optin {self.names(r.sender)}")
                if not self.names.known(r.sender):
                    self.echo(f"note: {r.sender} opted in but isn't in --names; they'd be shown as {r.sender}")
            elif cmd == "optout" and r.sender in optins:
                optins.remove(r.sender)
                done.append(f"optout {self.names(r.sender)}")
            elif cmd == "run":
                want_run = True
        if rows:
            state = {"last_rowid": rows[-1].rowid, "optins": optins}
            self.save_state(state)
        if want_run:
            done.append(self.run_wrapped(optins))
        return done

    def run_wrapped(self, optins: list[str]) -> str:
        now = self.clock()
        if self.last_run is not None and now - self.last_run < COOLDOWN_SECONDS:
            return "run skipped: cooldown"
        self.last_run = now
        if not optins:
            self.sender.send_text('Group Chat Wrapped: nobody has opted in yet. Reply "wrapped optin" to be in it.')
            return "run: nobody opted in"
        with closing(connect(self.db_path)) as conn:
            messages = to_messages(fetch_rows(conn, self._chat_id(conn)), self.names)
        opted = {self.names(k) for k in optins}
        with tempfile.TemporaryDirectory(prefix="wrapped-imessage-") as tmp:
            out = Path(self.out_dir) if self.out_dir else Path(tmp)
            try:
                story = self.story_maker(messages, opted, out, "Group Chat Wrapped", self.render_media)
            except render.RenderUnavailable as e:
                self.echo(f"render failed, nothing sent: {e}")
                return "run: render failed"
            awards = len(story.result["awards"])
            self.sender.send_text(
                f"Group Chat Wrapped: {len(messages):,} messages, {awards} awards. "
                f"Only the {len(opted)} who opted in are named."
            )
            for png in story.pngs:
                self.sender.send_file(png)
        return f"run: sent {len(story.pngs)} slides"

    def loop(self, interval: float = POLL_SECONDS) -> None:
        self.start()
        self.echo(f"watching {self.chat_guid} every {interval:g}s; ctrl-c to stop")
        while True:
            for line in self.poll_once():
                self.echo(line)
            time.sleep(interval)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wrapped-imessage", description="Group Chat Wrapped for one iMessage group.")
    p.add_argument("--chat-guid", help="the group's chat.guid, from --list-chats")
    p.add_argument("--list-chats", action="store_true", help="list group chats (no message text) and exit")
    p.add_argument("--names", help='JSON file: {"+15551234567": "Maya", "friend@icloud.com": "Jordan"}')
    p.add_argument("--me", default="Me", help="your own name in the slides")
    p.add_argument("--dry-run", action="store_true", help="print what would be sent instead of sending")
    p.add_argument("--db", default=str(DEFAULT_DB), help=argparse.SUPPRESS)
    p.add_argument("--interval", type=float, default=POLL_SECONDS, help="seconds between polls")
    p.add_argument("--out", help="keep the stats and slides here (default: a temporary folder)")
    args = p.parse_args(argv)

    if args.list_chats:
        with closing(connect(args.db)) as conn:
            for c in list_chats(conn):
                last = c["last"].strftime("%Y-%m-%d %H:%M") if c["last"] else "-"
                print(f"{c['guid']}\t{c['name'] or '(unnamed)'}\t{c['people']} people\tlast {last}")
        return 0
    if not args.chat_guid:
        p.error("--chat-guid is required (find it with --list-chats)")
    mapping = json.loads(Path(args.names).read_text(encoding="utf-8")) if args.names else {}
    sender = Sender(args.chat_guid, dry_run=args.dry_run)
    bridge = Bridge(args.chat_guid, sender, Names(mapping, args.me), db_path=Path(args.db),
                    out_dir=Path(args.out) if args.out else None)
    try:
        bridge.loop(args.interval)
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
