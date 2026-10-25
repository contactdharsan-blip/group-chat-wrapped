"""The Discord bot's award embeds and /wrapped-me, against fakes (no network, no discord.py needed)."""

import asyncio
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from test_discord_bot import FakeChannel, fake_msg
from wrapped import profiles
from wrapped.platforms import make_story
from wrapped.platforms.discord_bot import Handlers, OptinStore, award_embeds, hue_color, profile_embed
from wrapped.stats import compute

HAS_DISCORD = importlib.util.find_spec("discord") is not None


def chat():
    rows = []
    for i in range(12):
        rows.append((11, "Maya", f"OMW!!! round {i} 😂"))
        rows.append((12, "Jordan", f"where are you jordan? {i}"))
        rows.append((13, "Theo", "secret plans with Theo"))
    return [fake_msg(i, uid, name, text, minutes=i * 3) for i, (uid, name, text) in enumerate(rows)]


class SocialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = OptinStore(Path(self.tmp.name) / "optins.json")
        self.store.opt_in(1, 11, "Maya")

    def tearDown(self):
        self.tmp.cleanup()

    def test_run_posts_award_embeds_after_the_slides(self):
        h = Handlers(self.store, render_media=False, story_maker=make_story, web_url="https://example.test/")
        files, embeds = [], []

        async def send(paths):
            files.append(paths)

        async def send_embeds(batch):
            embeds.append(batch)

        asyncio.run(h.run(FakeChannel(1, chat()), "#floor-4", send, None, send_embeds))
        flat = [e for batch in embeds for e in batch]
        self.assertTrue(flat)
        self.assertTrue(all(len(b) <= 10 for b in embeds))
        for e in flat:
            self.assertEqual(e["author"]["name"], "Maya")
            self.assertEqual(e["color"], hue_color(profiles.hue("Maya")))
            self.assertTrue(e["description"])
            self.assertEqual(e["url"], "https://example.test/")
            self.assertLessEqual(max(len(f["value"]) for f in e["fields"]), 1024)
        text = json.dumps(flat, ensure_ascii=False).lower()
        self.assertNotIn("jordan", text)
        self.assertNotIn("theo", text)

    def test_run_without_embed_callback_is_unchanged(self):
        h = Handlers(self.store, render_media=False, story_maker=make_story)
        reply = asyncio.run(h.run(FakeChannel(1, chat()), "#floor-4", None))
        self.assertIn("awards", reply)

    def test_me_for_an_opted_in_member(self):
        h = Handlers(self.store)
        text, embed = asyncio.run(h.me(FakeChannel(1, chat()), 11))
        self.assertIsNone(text)
        self.assertTrue(embed["title"].startswith("Maya"))
        stats_field = embed["fields"][0]["value"]
        self.assertIn("12", stats_field)  # Maya's message count
        self.assertNotIn("url", embed)
        dumped = json.dumps(embed, ensure_ascii=False).lower()
        self.assertNotIn("jordan", dumped)
        self.assertNotIn("theo", dumped)

    def test_me_refuses_someone_not_opted_in_without_reading_history(self):
        h = Handlers(self.store)
        ch = FakeChannel(1, chat())
        text, embed = asyncio.run(h.me(ch, 12))
        self.assertIsNone(embed)
        self.assertIn("/wrapped optin", text)
        self.assertEqual(ch.history_calls, [])

    def test_profile_embed_links_only_when_configured(self):
        msgs = [fake_msg(i, 11, "Maya", "hello there 😂") for i in range(3)]
        from wrapped.platforms.discord_bot import to_message
        messages = [to_message(m, {"11": "Maya"}) for m in msgs]
        p = profiles.build(messages, compute(messages, {"Maya"}))[0]
        self.assertNotIn("url", profile_embed(p, "bio"))
        self.assertEqual(profile_embed(p, "bio", "https://x.test/")["url"], "https://x.test/")

    def test_award_embed_clips_long_receipts(self):
        result = {"awards": [{"key": "novelist", "title": "The Novelist", "winner": "Maya", "value_text": "v",
                              "detail": "", "receipt": {"author": "Maya", "ts": "2026-09-01T10:00:00", "text": "x" * 5000}}]}
        e = award_embeds(result, [], {"awards": {}})[0]
        self.assertLessEqual(len(e["fields"][1]["value"]), 1024)


@unittest.skipUnless(HAS_DISCORD, "discord.py is not installed")
class SocialWiringTests(unittest.TestCase):
    def test_wrapped_me_command_and_embeds_build(self):
        import discord

        from wrapped.platforms.discord_bot import build_bot
        with tempfile.TemporaryDirectory() as tmp:
            _, tree = build_bot(Handlers(OptinStore(Path(tmp) / "o.json")))
            self.assertIsNotNone(tree.get_command("wrapped-me"))
        result = {"awards": [{"key": "hype", "title": "Hype Machine", "winner": "Maya", "value_text": "3 messages",
                              "detail": "", "receipt": {"author": "Maya", "ts": "2026-09-01T10:00:00", "text": "OMG"}}]}
        e = discord.Embed.from_dict(award_embeds(result, [], {"awards": {"hype": "Loud."}})[0])
        self.assertEqual(e.title, "Hype Machine")


if __name__ == "__main__":
    unittest.main()
