"""The Discord bot against fakes: no network, and no discord.py needed except for the wiring test."""

import asyncio
import importlib.util
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace as NS

from wrapped import render
from wrapped.platforms import Story, make_story
from wrapped.platforms.discord_bot import Handlers, OptinStore, chunks, read_history, to_message

HAS_DISCORD = importlib.util.find_spec("discord") is not None
T0 = datetime(2026, 9, 1, 18, 0, tzinfo=timezone.utc)


def fake_msg(i, user_id, display, text, *, minutes=0, bot=False, kind="default", reply_to=None,
             reactions=(), attachments=0):
    return NS(
        id=1000 + i,
        author=NS(id=user_id, display_name=display, bot=bot),
        type=NS(name=kind),
        created_at=T0 + timedelta(minutes=minutes),
        content=text,
        reference=NS(message_id=reply_to) if reply_to else None,
        reactions=[NS(emoji=e, count=c) for e, c in reactions],
        attachments=[object()] * attachments,
    )


class FakeChannel:
    def __init__(self, cid, messages):
        self.id, self.name, self._messages, self.history_calls = cid, "floor-4", messages, []

    def history(self, limit=None, oldest_first=None):
        self.history_calls.append((limit, oldest_first))
        newest_first = sorted(self._messages, key=lambda m: m.created_at, reverse=True)[:limit]

        async def gen():
            for m in newest_first:
                yield m
        return gen()


def run(coro):
    return asyncio.run(coro)


class ConversionTests(unittest.TestCase):
    def test_converts_fields(self):
        dm = fake_msg(1, 11, "maya (nickname)", "omw", reply_to=999, reactions=[("😂", 2), ("😂", 1), ("🔥", 1)],
                      attachments=2)
        m = to_message(dm, {"11": "Maya"})
        self.assertEqual(m.author, "Maya")  # the opt-in name wins over today's nickname
        self.assertEqual(m.text, "omw")
        self.assertEqual(m.reply_to, "999")
        self.assertEqual(m.reactions, {"😂": 3, "🔥": 1})
        self.assertEqual(m.attachments, 2)
        self.assertIsNone(m.ts.tzinfo)
        self.assertEqual(m.ts, T0.astimezone().replace(tzinfo=None))

    def test_unopted_authors_are_keyed_by_id_not_display_name(self):
        # Their display name is kept only to scrub it from quotes, never as the author.
        m = to_message(fake_msg(1, 12, "jordan", "hi"), {"11": "Maya"})
        self.assertEqual(m.author, "user:12")
        self.assertIn("jordan", m.aliases)

    def test_mentions_become_names_only_for_opted_in_users(self):
        dm = fake_msg(1, 11, "Maya", "<@2> and <@!3> are you coming?? ask <@11> or <@&77> in <#55>")
        m = to_message(dm, {"11": "Maya"})
        self.assertEqual(m.text, "someone and someone are you coming?? ask @Maya or someone in #channel")

    def test_raw_mention_of_unopted_user_never_reaches_an_embed(self):
        from wrapped import captions, profiles
        from wrapped.platforms.discord_bot import award_embeds
        from wrapped.stats import compute
        dms = []
        for i in range(12):
            dms.append(fake_msg(2 * i, 1, "Maya", "<@2> are you coming tonight?? <@2>", minutes=180 * i))
            dms.append(fake_msg(2 * i + 1, 2, "SecretSam", "maybe", minutes=180 * i + 90))
        names = {"1": "Maya"}
        msgs = [to_message(d, names) for d in dms]
        res = compute(msgs, set(names.values()))
        people = profiles.build(msgs, res)
        embeds = award_embeds(res, people, captions.templates(res["awards"], people))
        self.assertTrue(embeds)
        blob = str(embeds)
        self.assertNotIn("<@", blob)
        self.assertNotIn("SecretSam", blob)
        self.assertIn("someone are you coming tonight?? someone", blob)

    def test_unopted_display_names_are_still_scrubbed_from_quotes(self):
        from wrapped.stats import compute
        names = {"1": "Maya"}
        dms = [fake_msg(1, 1, "Maya", "is Jordan coming? jordan??"), fake_msg(2, 2, "Jordan", "no", minutes=1)]
        res = compute([to_message(d, names) for d in dms], set(names.values()))
        self.assertTrue(res["awards"])
        for a in res["awards"]:
            self.assertEqual(a["receipt"]["text"], "is someone coming? someone??")

    def test_unopted_user_with_an_opted_in_display_name_is_not_merged(self):
        from wrapped.stats import compute
        names = {"1": "Maya"}
        dms = [
            fake_msg(1, 1, "Maya", "real maya says hi"),
            fake_msg(2, 3, "Maya", "IMPOSTOR MESSAGE nobody consented to!!!", minutes=1),
        ]
        msgs = [to_message(d, names) for d in dms]
        res = compute(msgs, set(names.values()))
        self.assertEqual(res["members"], ["Maya"])
        self.assertEqual(res["group"]["share"], {"Maya": 1, "someone": 1})
        blob = str(res)
        self.assertNotIn("IMPOSTOR", blob)
        self.assertNotIn("user:3", blob)

    def test_skips_bots_and_system_messages(self):
        self.assertIsNone(to_message(fake_msg(1, 99, "Wrapped", "here you go", bot=True), {}))
        self.assertIsNone(to_message(fake_msg(2, 11, "Maya", "", kind="pins_add"), {}))
        self.assertIsNotNone(to_message(fake_msg(3, 11, "Maya", "yes", kind="reply"), {}))

    def test_history_is_sorted_and_reports_progress(self):
        from wrapped.platforms import discord_bot
        msgs = [fake_msg(i, 11, "Maya", f"m{i}", minutes=i) for i in range(5)]
        ch = FakeChannel(1, msgs)
        seen = []

        async def progress(n):
            seen.append(n)
        old, discord_bot.PROGRESS_EVERY = discord_bot.PROGRESS_EVERY, 2
        try:
            out = run(read_history(ch.history(limit=10), {}, progress))
        finally:
            discord_bot.PROGRESS_EVERY = old
        self.assertEqual([m.text for m in out], ["m0", "m1", "m2", "m3", "m4"])
        self.assertEqual(seen, [2, 4])

    def test_chunks_of_ten(self):
        self.assertEqual([len(c) for c in chunks(list(range(23)))], [10, 10, 3])
        self.assertEqual(chunks([]), [])


class OptinStoreTests(unittest.TestCase):
    def test_per_channel_and_persistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sub" / "optins.json"
            s = OptinStore(path)
            s.opt_in(1, 11, "Maya")
            s.opt_in(2, 12, "Jordan")
            self.assertEqual(OptinStore(path).names(1), {"11": "Maya"})
            self.assertEqual(OptinStore(path).names(2), {"12": "Jordan"})
            self.assertTrue(s.opt_out(1, 11))
            self.assertFalse(s.opt_out(1, 11))
            self.assertEqual(OptinStore(path).names(1), {})


class HandlerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = OptinStore(Path(self.tmp.name) / "optins.json")

    def tearDown(self):
        self.tmp.cleanup()

    def chat(self):
        rows = [
            (11, "Maya", "omw!!!"), (12, "Jordan", "where are you?"), (13, "Theo", "secret plans with Theo"),
            (11, "Maya", "almost there"), (12, "Jordan", "ok"), (99, "Wrapped", "bot noise"),
        ]
        return [fake_msg(i, uid, name, text, minutes=i * 7, bot=(uid == 99)) for i, (uid, name, text) in enumerate(rows)]

    def test_optin_and_optout_replies(self):
        h = Handlers(self.store)
        self.assertIn("Maya", h.optin(1, 11, "Maya"))
        self.assertIn("out", h.optout(1, 11))
        self.assertIn("weren't", h.optout(1, 11))

    def test_run_without_optins_reads_nothing(self):
        h = Handlers(self.store)
        ch = FakeChannel(1, self.chat())
        reply = run(h.run(ch, "#floor-4", send=None))
        self.assertIn("/wrapped optin", reply)
        self.assertEqual(ch.history_calls, [])

    def test_run_posts_slides_in_groups_of_ten_then_the_video(self):
        captured = {}

        def fake_story(messages, opted, out, name, render_media):
            captured.update(messages=messages, opted=opted, name=name)
            pngs = []
            for i in range(14):
                pngs.append(out / f"slide-{i + 1:02d}.png")
                pngs[-1].write_bytes(b"png")
            video = out / "wrapped.mp4"
            video.write_bytes(b"mp4")
            return Story(result={"awards": [1, 2], "members": sorted(opted)}, html=out / "slides.html",
                         pngs=pngs, video=video)

        h = Handlers(self.store, limit=500, story_maker=fake_story)
        h.optin(1, 11, "Maya")
        h.optin(1, 12, "Jordan")
        ch = FakeChannel(1, self.chat())
        posts = []

        async def send(paths):
            self.assertTrue(all(p.exists() for p in paths))  # files exist while being posted
            posts.append([p.name for p in paths])

        reply = run(h.run(ch, "#floor-4", send))
        self.assertEqual(ch.history_calls, [(500, False)])
        self.assertEqual([len(p) for p in posts], [10, 4, 1])
        self.assertEqual(posts[-1], ["wrapped.mp4"])
        self.assertEqual(captured["opted"], {"Maya", "Jordan"})
        self.assertEqual(captured["name"], "#floor-4")
        self.assertNotIn("bot noise", [m.text for m in captured["messages"]])
        self.assertIn("Wrapped 5 messages", reply)

    def test_oversized_video_is_not_posted(self):
        from wrapped.platforms import discord_bot

        def fake_story(messages, opted, out, name, render_media):
            png, video = out / "slide-01.png", out / "wrapped.mp4"
            png.write_bytes(b"png")
            video.write_bytes(b"x" * 20)
            return Story(result={"awards": [], "members": []}, html=out / "s.html", pngs=[png], video=video)

        h = Handlers(self.store, story_maker=fake_story)
        h.optin(1, 11, "Maya")
        posts = []

        async def send(paths):
            posts.append(paths)
        old, discord_bot.MAX_UPLOAD_BYTES = discord_bot.MAX_UPLOAD_BYTES, 10
        try:
            reply = run(h.run(FakeChannel(1, self.chat()), "#floor-4", send))
        finally:
            discord_bot.MAX_UPLOAD_BYTES = old
        self.assertEqual(len(posts), 1)
        self.assertIn("10 MB", reply)

    def test_render_failure_is_reported_not_raised(self):
        def broken(*a):
            raise render.RenderUnavailable("no webkit")

        h = Handlers(self.store, story_maker=broken)
        h.optin(1, 11, "Maya")
        reply = run(h.run(FakeChannel(1, self.chat()), "#floor-4", send=None))
        self.assertIn("no webkit", reply)

    def test_make_story_refuses_an_empty_chat_clearly(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "no messages"):
                make_story([], {"Maya"}, Path(tmp), "x", render_media=False)

    def test_real_pipeline_hides_unopted_members(self):
        # make_story without rendering: only Maya opted in, so Jordan and Theo never appear by name.
        h = Handlers(self.store, render_media=False, story_maker=make_story)
        h.optin(1, 11, "Maya")
        seen = {}

        def keep(messages, opted, out, name, render_media):
            story = make_story(messages, opted, out, name, render_media)
            seen["stats"] = (out / "stats.json").read_text(encoding="utf-8").lower()
            seen["html"] = story.html.read_text(encoding="utf-8").lower()
            return story

        h.story_maker = keep
        run(h.run(FakeChannel(1, self.chat()), "#floor-4", send=None))
        for text in seen.values():
            self.assertNotIn("jordan", text)
            self.assertNotIn("theo", text)


@unittest.skipUnless(HAS_DISCORD, "discord.py is not installed: install it into .venv to test the bot wiring "
                                  "(README, Platforms > Discord)")
class WiringTests(unittest.TestCase):
    def test_command_group_and_intents(self):
        from wrapped.platforms.discord_bot import build_bot
        with tempfile.TemporaryDirectory() as tmp:
            client, tree = build_bot(Handlers(OptinStore(Path(tmp) / "o.json")))
            self.assertTrue(client.intents.message_content)
            group = tree.get_command("wrapped")
            self.assertIsNotNone(group)
            self.assertEqual(sorted(c.name for c in group.commands), ["me", "optin", "optout", "run"])


if __name__ == "__main__":
    unittest.main()
