"""Locks the demo's story: each award goes to the friend it was written for,
with the receipt the pitch relies on. A generator tweak that breaks the story
fails here, not on stage."""

import importlib.util
import unittest
from pathlib import Path

from helpers import assert_receipts_real
from wrapped.importers import load
from wrapped.stats import compute

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "demo" / "demo-chat.txt"
CAST = {"Maya", "Jordan", "Priya", "Theo"}


class DemoStoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.messages = load(DEMO, "whatsapp")
        cls.result = compute(cls.messages, CAST)
        cls.awards = {a["key"]: a for a in cls.result["awards"]}

    def test_generator_reproduces_committed_file(self):
        spec = importlib.util.spec_from_file_location("make_demo_chat", ROOT / "demo" / "make_demo_chat.py")
        gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gen)
        gen.build()
        self.assertEqual(gen.render(), DEMO.read_text(encoding="utf-8"))

    def test_shape(self):
        g = self.result["group"]
        self.assertTrue(1500 <= g["messages"] <= 2500, g["messages"])
        self.assertTrue(g["first"].startswith("2026-08-19"))
        self.assertTrue(g["last"].startswith("2026-12-12"))
        self.assertEqual({m.author for m in self.messages}, CAST)  # system lines dropped
        self.assertTrue(any("\n" in m.text for m in self.messages))  # multi-line paragraphs
        self.assertGreater(g["media"], 10)

    def test_every_award_present_and_real(self):
        self.assertEqual(len(self.awards), 11)
        assert_receipts_real(self, self.result, self.messages)

    def test_winners(self):
        expected = {
            "main_character": "Maya",
            "novelist": "Priya",
            "three_am": "Priya",
            "omw": "Jordan",
            "left_on_read": "Theo",
            "hype": "Maya",
            "speed_demon": "Maya",
            "ghost": "Theo",
            "emoji": "Jordan",
            "group_word": "Theo",
            "busiest_day": "Maya",
        }
        self.assertEqual({k: a["winner"] for k, a in self.awards.items()}, expected)

    def test_receipts_tell_the_story(self):
        a = self.awards
        self.assertEqual(a["main_character"]["receipt"]["text"], "ok I need to rant")
        self.assertIn("dining hall menu", a["novelist"]["receipt"]["text"])
        self.assertIn(a["three_am"]["receipt"]["ts"][11:13], {"01", "02", "03", "04"})
        self.assertIn("don't go in without me", a["omw"]["receipt"]["text"])
        self.assertIn("thanksgiving", a["left_on_read"]["receipt"]["text"])
        self.assertIn("WE BEAT STATE", a["hype"]["receipt"]["text"])
        self.assertEqual(a["ghost"]["receipt"]["text"], "k")
        self.assertEqual(a["emoji"]["emoji"], "\U0001F480")
        self.assertEqual(a["group_word"]["word"], "bingus")
        self.assertIn("decided his name is Bingus", a["group_word"]["receipt"]["text"])
        self.assertEqual(a["busiest_day"]["date"], "2026-11-21")


if __name__ == "__main__":
    unittest.main()
