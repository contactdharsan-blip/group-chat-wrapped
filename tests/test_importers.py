import json
import unittest
from datetime import datetime

from wrapped.importers import parse_csv, parse_discord, parse_whatsapp

NNBSP = " "
LRM = "‎"

IOS = (
    f"[8/19/26, 9:00:00{NNBSP}AM] Wolfpack: {LRM}Messages and calls are end-to-end encrypted. No one outside of this chat can read them.\n"
    f"[8/19/26, 9:00:05{NNBSP}AM] Wolfpack: {LRM}Ana created group “Wolfpack”\n"
    f"[8/19/26, 9:41:03{NNBSP}PM] Ana: hello: is this thing on\n"
    f"[8/19/26, 9:42:10{NNBSP}PM] Ben: first line\n"
    "second line\n"
    "\n"
    "third line after a blank\n"
    f"[8/19/26, 12:05:00{NNBSP}AM] Ana: {LRM}image omitted\n"
    f"[8/20/26, 12:30:00{NNBSP}PM] Ben: I added the slides and then I left\n"
    f"[8/20/26, 1:00:00{NNBSP}PM] Ana: {LRM}This message was deleted\n"
)

ANDROID = (
    "24/10/26, 21:41 - Messages and calls are end-to-end encrypted. No one outside of this chat, not even WhatsApp, can read or listen to them. Tap to learn more.\n"
    "24/10/26, 21:41 - Ana created group \"Wolfpack\"\n"
    "24/10/26, 21:41 - Ana: hey\n"
    "24/10/26, 21:45 - Ben: <Media omitted>\n"
    "25/10/26, 07:02 - Ben: line one\n"
    "line two\n"
    "25/10/26, 07:03 - Ana added Cy\n"
)


class WhatsAppTests(unittest.TestCase):
    def test_ios_format(self):
        msgs = parse_whatsapp(IOS)
        self.assertEqual([m.author for m in msgs], ["Ana", "Ana", "Ben", "Ben"])
        # sorted oldest first: the 12:05 AM image is from the morning of 8/19
        self.assertEqual(msgs[0].ts, datetime(2026, 8, 19, 0, 5, 0))
        self.assertEqual(msgs[0].attachments, 1)
        self.assertEqual(msgs[0].text, "")
        self.assertEqual(msgs[1].ts, datetime(2026, 8, 19, 21, 41, 3))
        self.assertEqual(msgs[1].text, "hello: is this thing on")

    def test_ios_multiline_and_lookalike_text(self):
        msgs = parse_whatsapp(IOS)
        self.assertEqual(msgs[2].text, "first line\nsecond line\n\nthird line after a blank")
        # a real message that merely contains "added"/"left" is kept
        self.assertEqual(msgs[3].text, "I added the slides and then I left")
        self.assertEqual(msgs[3].ts, datetime(2026, 8, 20, 12, 30, 0))

    def test_android_format_day_first(self):
        msgs = parse_whatsapp(ANDROID)
        self.assertEqual(len(msgs), 3)
        self.assertEqual(msgs[0].ts, datetime(2026, 10, 24, 21, 41))
        self.assertEqual(msgs[0].text, "hey")
        self.assertEqual(msgs[1].attachments, 1)
        self.assertEqual(msgs[2].text, "line one\nline two")

    def test_android_us_twelve_hour(self):
        text = "10/24/26, 9:41 PM - Ana: hi\n10/25/26, 12:01 AM - Ben: late\n"
        msgs = parse_whatsapp(text)
        self.assertEqual(msgs[0].ts, datetime(2026, 10, 24, 21, 41))
        self.assertEqual(msgs[1].ts, datetime(2026, 10, 25, 0, 1))


class DiscordTests(unittest.TestCase):
    def test_exporter_shape(self):
        data = {
            "guild": {"name": "x"},
            "messages": [
                {
                    "id": "2",
                    "type": "Reply",
                    "timestamp": "2026-10-24T03:10:00.123-07:00",
                    "content": "answer",
                    "author": {"name": "ben"},
                    "reference": {"messageId": "1"},
                    "reactions": [{"emoji": {"name": "\U0001F602"}, "count": 3}],
                    "attachments": [{"url": "a.png"}],
                },
                {
                    "id": "1",
                    "type": "Default",
                    "timestamp": "2026-10-24T03:00:00-07:00",
                    "content": "question?",
                    "author": {"name": "ana"},
                    "reactions": [],
                    "attachments": [],
                },
                {"id": "3", "type": "GuildMemberJoin", "timestamp": "2026-10-24T04:00:00-07:00", "content": "", "author": {"name": "cy"}},
            ],
        }
        msgs = parse_discord(json.dumps(data))
        self.assertEqual([m.author for m in msgs], ["ana", "ben"])
        self.assertEqual(msgs[0].ts, datetime(2026, 10, 24, 3, 0))  # wall clock kept
        self.assertIsNone(msgs[0].ts.tzinfo)
        self.assertEqual(msgs[1].reply_to, "1")
        self.assertEqual(msgs[1].reactions, {"\U0001F602": 3})
        self.assertEqual(msgs[1].attachments, 1)


class CsvTests(unittest.TestCase):
    def test_csv(self):
        text = 'timestamp,author,text\n2026-10-24 21:41:00,Ana,"hi, all"\n2026-10-24T21:40:00,Ben,"multi\nline"\n'
        msgs = parse_csv(text)
        self.assertEqual([m.author for m in msgs], ["Ben", "Ana"])
        self.assertEqual(msgs[1].text, "hi, all")
        self.assertEqual(msgs[0].text, "multi\nline")


if __name__ == "__main__":
    unittest.main()
