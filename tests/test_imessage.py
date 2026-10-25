"""The iMessage bridge against a tiny fake chat.db in a temp folder. Nothing is ever sent."""

import json
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace as NS

from wrapped.platforms import Story
from wrapped.platforms.imessage import (
    APPLE_EPOCH, Bridge, Names, Sender, apple_time, clean, connect, decode_attributed_body, fetch_rows,
    is_group_guid, list_chats, main, parse_command, to_messages,
)

GROUP = "any;+;chat111111"
OTHER_GROUP = "any;+;chat222222"
DM = "any;-;+15550000002"
BASE = datetime(2026, 9, 1, 18, 0).timestamp()  # local wall clock


def apple_ns(minutes: float) -> int:
    return int((BASE + minutes * 60 - APPLE_EPOCH) * 1e9)


def typedstream(text: str) -> bytes:
    """An attributedBody shaped like the ones Messages writes."""
    raw = text.encode("utf-8")
    if len(raw) < 0x80:
        size = bytes([len(raw)])
    elif len(raw) < 0x10000:
        size = b"\x81" + len(raw).to_bytes(2, "little")
    else:
        size = b"\x82" + len(raw).to_bytes(4, "little")
    head = (b"\x04\x0bstreamtyped\x81\xe8\x03\x84\x01@\x84\x84\x84\x12NSAttributedString\x00"
            b"\x84\x84\x08NSObject\x00\x85\x92\x84\x84\x84\x08NSString\x01\x94\x84\x01+")
    tail = (b"\x86\x84\x02iI\x01\x05\x92\x84\x84\x84\x0cNSDictionary\x00\x94\x84\x01i\x01\x92\x84\x96\x96"
            b"\x1d__kIMMessagePartAttributeName\x86\x92\x84\x84\x84\x08NSNumber\x00\x84\x84\x07NSValue\x00"
            b"\x94\x84\x01*\x84\x99\x99\x00\x86\x86\x86")
    return head + size + raw + tail


SCHEMA = """
CREATE TABLE chat (ROWID INTEGER PRIMARY KEY AUTOINCREMENT, guid TEXT, display_name TEXT, style INTEGER);
CREATE TABLE handle (ROWID INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT);
CREATE TABLE chat_handle_join (chat_id INTEGER, handle_id INTEGER);
CREATE TABLE chat_message_join (chat_id INTEGER, message_id INTEGER, message_date INTEGER);
CREATE TABLE message (ROWID INTEGER PRIMARY KEY AUTOINCREMENT, guid TEXT, text TEXT, attributedBody BLOB,
    handle_id INTEGER, date INTEGER, is_from_me INTEGER, cache_has_attachments INTEGER,
    associated_message_type INTEGER, associated_message_guid TEXT, thread_originator_guid TEXT,
    item_type INTEGER);
"""


class FakeDb:
    def __init__(self, path: Path):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.executescript(SCHEMA)
        self.handles = {}
        for h in ("+15550000001", "+15550000002", "jordan@example.com"):
            self.handles[h] = self.conn.execute("INSERT INTO handle (id) VALUES (?)", (h,)).lastrowid
        self.group = self.chat(GROUP, "Floor 4 Survivors", 43, ["+15550000001", "jordan@example.com"])
        self.other = self.chat(OTHER_GROUP, "Other group", 43, ["+15550000002"])
        self.dm = self.chat(DM, "", 45, ["+15550000002"])
        self.minute = 0
        self.conn.commit()

    def chat(self, guid, name, style, handles):
        cid = self.conn.execute("INSERT INTO chat (guid, display_name, style) VALUES (?,?,?)",
                                (guid, name, style)).lastrowid
        for h in handles:
            self.conn.execute("INSERT INTO chat_handle_join VALUES (?,?)", (cid, self.handles[h]))
        return cid

    def add(self, sender, text=None, *, chat=None, body=None, attach=0, tapback=0, target=None, reply=None,
            event=0):
        self.minute += 5
        n = self.conn.execute("SELECT COUNT(*) FROM message").fetchone()[0] + 1
        guid = f"MSG-{n}"
        from_me = sender == "me"
        self.conn.execute(
            "INSERT INTO message (guid, text, attributedBody, handle_id, date, is_from_me, cache_has_attachments,"
            " associated_message_type, associated_message_guid, thread_originator_guid, item_type)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (guid, text, body, 0 if from_me else self.handles[sender], apple_ns(self.minute), int(from_me),
             attach, tapback, target, reply, event),
        )
        rowid = self.conn.execute("SELECT MAX(ROWID) FROM message").fetchone()[0]
        self.conn.execute("INSERT INTO chat_message_join VALUES (?,?,?)",
                          (chat or self.group, rowid, apple_ns(self.minute)))
        self.conn.commit()
        return guid


class FakeRun:
    def __init__(self):
        self.calls = []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        return NS(returncode=0, stderr="")


class DecoderTests(unittest.TestCase):
    def test_short_long_and_emoji(self):
        for text in ("omw", "omw 😭 ​ ok", "x" * 127, "y" * 128, "long paragraph 💬 " * 40, "z" * 70_000):
            self.assertEqual(decode_attributed_body(typedstream(text)), text)

    def test_mutable_string_class(self):
        blob = typedstream("edited 😂").replace(b"\x08NSString", b"\x0fNSMutableString")
        self.assertEqual(decode_attributed_body(blob), "edited 😂")

    def test_bad_blobs_give_none(self):
        self.assertIsNone(decode_attributed_body(None))
        self.assertIsNone(decode_attributed_body(b""))
        self.assertIsNone(decode_attributed_body(b"no class here"))
        blob = typedstream("hello world")
        self.assertIsNone(decode_attributed_body(blob[:blob.find(b"hello") + 3]))  # cut inside the text
        self.assertIsNone(decode_attributed_body(typedstream("é").replace("é".encode(), b"\xff\xfe")))

    def test_clean_and_time(self):
        self.assertEqual(clean("￼ hi​‌‍⁠﻿ "), "hi")
        self.assertEqual(apple_time(apple_ns(0)), datetime(2026, 9, 1, 18, 0))
        self.assertEqual(apple_time(int(BASE - APPLE_EPOCH)), datetime(2026, 9, 1, 18, 0))  # seconds, pre-10.13

    def test_commands(self):
        self.assertEqual(parse_command("Wrapped"), "run")
        self.assertEqual(parse_command("  wrapped   OPTIN "), "optin")
        self.assertEqual(parse_command("wrapped optout"), "optout")
        self.assertIsNone(parse_command("is the wrapped thing out yet"))


class ReadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = FakeDb(Path(self.tmp.name) / "chat.db")

    def tearDown(self):
        self.db.conn.close()
        self.tmp.cleanup()

    def test_rows_messages_and_tapbacks(self):
        first = self.db.add("+15550000001", "omw!!!")
        self.db.add("jordan@example.com", None, body=typedstream("where are you 😭"))
        self.db.add("me", "￼", attach=1)
        self.db.add("jordan@example.com", "Laughed at “omw!!!”", tapback=2003, target=f"p:0/{first}")
        self.db.add("+15550000001", "Loved it", tapback=2000, target=f"bp:{first}")
        self.db.add("+15550000001", "removed", tapback=3000, target=f"p:0/{first}")
        self.db.add("me", "named the group", event=2)
        self.db.add("me", "wrapped optin")
        self.db.add("+15550000001", "sure", reply=first)
        self.db.add("+15550000002", "other chat secret", chat=self.db.other)
        with connect(self.db.path) as conn:
            rows = fetch_rows(conn, self.db.group)
        self.assertEqual(len(rows), 9)  # nothing from the other chat
        names = Names({"+15550000001": "Maya", "jordan@example.com": "Jordan"}, me="Dharsan")
        msgs = to_messages(rows, names)
        self.assertEqual([(m.author, m.text) for m in msgs],
                         [("Maya", "omw!!!"), ("Jordan", "where are you 😭"), ("Dharsan", ""), ("Maya", "sure")])
        self.assertEqual(msgs[0].reactions, {"😂": 1, "❤️": 1})
        self.assertEqual(msgs[0].ts, datetime(2026, 9, 1, 18, 5))
        self.assertEqual(msgs[2].attachments, 1)
        self.assertEqual(msgs[3].reply_to, first)

    def test_read_only(self):
        with connect(self.db.path) as conn, self.assertRaises(sqlite3.OperationalError):
            conn.execute("DELETE FROM message")

    def test_list_chats_is_groups_only_and_has_no_text(self):
        self.db.add("+15550000001", "very private text")
        with connect(self.db.path) as conn:
            chats = list_chats(conn)
        self.assertEqual([c["guid"] for c in chats], [GROUP, OTHER_GROUP])
        self.assertEqual(chats[0]["people"], 3)
        self.assertEqual(chats[0]["last"], datetime(2026, 9, 1, 18, 5))
        self.assertIsNone(chats[1]["last"])

    def test_list_chats_cli_prints_no_message_text(self):
        self.db.add("+15550000001", "very private text")
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(main(["--list-chats", "--db", str(self.db.path)]), 0)
        out = buf.getvalue()
        self.assertIn(GROUP, out)
        self.assertIn("Floor 4 Survivors", out)
        self.assertNotIn(DM, out)
        self.assertNotIn("private", out)


class SenderTests(unittest.TestCase):
    def test_refuses_anything_but_a_group(self):
        for bad in (DM, "", "+15550000002", "iMessage;-;friend@example.com"):
            with self.assertRaises(ValueError):
                Sender(bad)
        self.assertTrue(is_group_guid(GROUP))

    def test_dry_run_is_the_default_and_sends_nothing(self):
        run, printed = FakeRun(), []
        s = Sender(GROUP, run=run, echo=printed.append)
        s.send_text("hello")
        s.send_file(Path("/nowhere/slide-01.png"))
        self.assertEqual(run.calls, [])
        self.assertEqual(len(printed), 2)
        self.assertIn(GROUP, printed[0])

    def test_osascript_gets_the_bound_chat_as_an_argument(self):
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / "slide-01.png"
            png.write_bytes(b"png")
            run = FakeRun()
            s = Sender(GROUP, dry_run=False, stage_dir=Path(tmp) / "stage", run=run)
            s.send_text('hi" to chat id "any;+;evil')
            s.send_file(png)
            self.assertEqual(len(run.calls), 2)
            for cmd in run.calls:
                self.assertEqual(cmd[0], "osascript")
                self.assertEqual(cmd[-1], GROUP)  # the chat id is always the bound one, passed as argv
                script = " ".join(cmd[1:-2])
                self.assertNotIn("evil", script)
                self.assertNotIn(GROUP, script)
            self.assertEqual(run.calls[0][-2], 'hi" to chat id "any;+;evil')
            staged = Path(run.calls[1][-2])
            self.assertEqual(staged.parent, Path(tmp) / "stage")
            self.assertTrue(staged.exists())

    def test_bridge_refuses_a_sender_for_another_chat(self):
        with self.assertRaises(ValueError):
            Bridge(GROUP, Sender(OTHER_GROUP), Names())


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.db = FakeDb(root / "chat.db")
        self.printed = []
        self.sender = Sender(GROUP, echo=self.printed.append)  # dry run
        self.sent = []
        self.sender.send_text = lambda text: self.sent.append(("text", text))
        self.sender.send_file = lambda path: self.sent.append(("file", Path(path).name))
        self.now = 1_000_000.0
        self.made = {}
        self.bridge = Bridge(
            GROUP, self.sender, Names({"+15550000001": "Maya", "jordan@example.com": "Jordan"}, me="Dharsan"),
            db_path=self.db.path, state_path=root / "state.json", story_maker=self.fake_story,
            clock=lambda: self.now, echo=self.printed.append,
        )

    def tearDown(self):
        self.db.conn.close()
        self.tmp.cleanup()

    def fake_story(self, messages, opted, out, name, render_media):
        self.made = {"messages": messages, "opted": opted}
        pngs = []
        for i in range(3):
            pngs.append(out / f"slide-{i + 1:02d}.png")
            pngs[-1].write_bytes(b"png")
        return Story(result={"awards": [1], "members": sorted(opted)}, html=out / "s.html", pngs=pngs)

    def test_old_commands_do_not_fire_on_first_start(self):
        self.db.add("+15550000001", "wrapped optin")
        self.db.add("+15550000001", "wrapped")
        self.assertEqual(self.bridge.poll_once(), [])
        self.assertEqual(self.sent, [])
        self.assertEqual(json.loads(self.bridge.state_path.read_text())["last_rowid"], 2)

    def test_optin_optout_and_run(self):
        self.bridge.start()
        self.db.add("+15550000001", "omw!!!")
        self.db.add("jordan@example.com", "where are you")
        self.db.add("+15550000001", "Wrapped optin")
        self.db.add("me", "wrapped optin")
        self.db.add("jordan@example.com", "wrapped optin")
        self.db.add("jordan@example.com", "wrapped optout")
        self.assertEqual(self.bridge.poll_once(), ["optin Maya", "optin Dharsan", "optin Jordan", "optout Jordan"])
        self.assertEqual(self.sent, [])
        self.db.add("jordan@example.com", "wrapped")
        done = self.bridge.poll_once()
        self.assertEqual(done, ["run: sent 3 slides"])
        self.assertEqual(self.made["opted"], {"Maya", "Dharsan"})
        self.assertEqual([m.text for m in self.made["messages"]], ["omw!!!", "where are you"])  # no commands
        self.assertEqual(self.sent[0][0], "text")
        self.assertEqual([s for s in self.sent[1:]], [("file", "slide-01.png"), ("file", "slide-02.png"),
                                                     ("file", "slide-03.png")])
        # a second poll with nothing new does nothing
        self.sent.clear()
        self.assertEqual(self.bridge.poll_once(), [])
        self.assertEqual(self.sent, [])
        # state survives a restart
        state = json.loads(self.bridge.state_path.read_text())
        self.assertEqual(state["optins"], ["+15550000001", "me"])

    def test_cooldown_and_nobody_opted_in(self):
        self.bridge.start()
        self.db.add("+15550000001", "wrapped")
        self.assertEqual(self.bridge.poll_once(), ["run: nobody opted in"])
        self.assertIn("wrapped optin", self.sent[0][1])
        self.db.add("+15550000001", "wrapped")
        self.assertEqual(self.bridge.poll_once(), ["run skipped: cooldown"])
        self.assertEqual(len(self.sent), 1)

    def test_run_with_only_commands_says_there_is_nothing_to_wrap(self):
        bridge = Bridge(GROUP, self.sender, Names({"+15550000001": "Maya"}), db_path=self.db.path,
                        state_path=Path(self.tmp.name) / "s4.json", render_media=False, echo=self.printed.append)
        bridge.start()
        self.db.add("+15550000001", "wrapped optin")
        self.db.add("+15550000001", "wrapped")
        self.assertEqual(bridge.poll_once(), ["optin Maya", "run: no messages"])
        self.assertEqual(len(self.sent), 1)
        self.assertIn("no messages", self.sent[0][1])

    def test_other_chats_never_trigger_anything(self):
        self.bridge.start()
        self.db.add("+15550000002", "wrapped optin", chat=self.db.other)
        self.db.add("+15550000002", "wrapped", chat=self.db.dm)
        self.assertEqual(self.bridge.poll_once(), [])
        self.assertEqual(self.sent, [])

    def test_unknown_chat_guid_exits(self):
        bridge = Bridge("any;+;missing", Sender("any;+;missing"), Names(), db_path=self.db.path,
                        state_path=Path(self.tmp.name) / "s2.json")
        with self.assertRaises(SystemExit):
            bridge.start()

    def test_real_pipeline_without_render_in_dry_run(self):
        # The real make_story (no PNGs) and the real dry-run Sender, end to end.
        printed = []
        bridge = Bridge(GROUP, Sender(GROUP, echo=printed.append), Names({"+15550000001": "Maya"}),
                        db_path=self.db.path, state_path=Path(self.tmp.name) / "s3.json", render_media=False,
                        echo=printed.append)
        bridge.start()
        self.db.add("+15550000001", "omw!!!")
        self.db.add("jordan@example.com", "secret from jordan@example.com")
        self.db.add("+15550000001", "wrapped optin")
        self.db.add("+15550000001", "wrapped")
        self.assertEqual(bridge.poll_once(), ["optin Maya", "run: sent 0 slides"])
        self.assertEqual(len(printed), 1)
        self.assertTrue(printed[0].startswith(f"[dry run] would send to {GROUP}: Group Chat Wrapped: 2 messages"))


if __name__ == "__main__":
    unittest.main()
