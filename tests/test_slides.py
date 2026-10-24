import re
import unittest

from helpers import chat
from wrapped import slides
from wrapped.stats import compute


def sample():
    rows = [("Ana", f"2026-09-0{i + 1} 03:00", f"<script>alert(1)</script> omw!!! deep thought {i}?") for i in range(5)]
    rows += [("Ben", f"2026-09-0{i + 1} 10:00", "ok") for i in range(5)]
    rows += [("Zed", "2026-09-07 10:00", "secret from zed")]
    return chat(*rows)


class SlidesTests(unittest.TestCase):
    def setUp(self):
        self.result = compute(sample(), {"Ana", "Ben"})
        self.html = slides.build_html(self.result, "Test Chat")

    def test_one_slide_per_award_plus_title_totals_closing(self):
        ids = re.findall(r'<section class="slide" id="(slide-\d\d)"', self.html)
        self.assertEqual(len(ids), len(self.result["awards"]) + 3)
        self.assertEqual(ids, [f"slide-{n:02d}" for n in range(1, len(ids) + 1)])

    def test_self_contained(self):
        self.assertTrue(self.html.startswith("<!doctype html>"))
        self.assertNotRegex(self.html, r'(src|href)=["\']?(https?:)?//')
        self.assertNotIn("<link", self.html)

    def test_receipts_escaped(self):
        self.assertNotIn("<script>", self.html)
        self.assertIn("&lt;script&gt;", self.html)

    def test_non_opted_name_absent(self):
        self.assertNotIn("zed", self.html.lower())

    def test_every_receipt_and_date_on_its_slide(self):
        for award in self.result["awards"]:
            self.assertIn(slides._when(award["receipt"]["ts"]), self.html, award["title"])

    def test_safe_zone_css(self):
        self.assertGreaterEqual(slides.SAFE_BOTTOM, 350)
        self.assertGreaterEqual(slides.SAFE_RIGHT, 120)
        self.assertIn(f"bottom: {slides.SAFE_BOTTOM}px", self.html)
        self.assertIn(f"right: {slides.SAFE_RIGHT}px", self.html)
        self.assertIn("width: 1080px; height: 1920px", self.html)

    def test_no_emoji_section_markers(self):
        for label in re.findall(r'<div class="(?:title|count|kicker)">([^<]*)</div>', self.html):
            self.assertTrue(label.isascii() or all(ord(c) < 0x2600 for c in label), label)


if __name__ == "__main__":
    unittest.main()
