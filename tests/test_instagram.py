import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from wrapped.importers import _unmojibake, load, load_instagram, parse_instagram

ROOT = Path(__file__).resolve().parent.parent
FOLDER = ROOT / "tests" / "fixtures" / "instagram" / "floor4"


class InstagramTests(unittest.TestCase):
    def test_mojibake_is_repaired_and_clean_text_is_left_alone(self):
        self.assertEqual(_unmojibake("omw ð\u009f\u0098­"), "omw 😭")
        self.assertEqual(_unmojibake("RenÃ©e"), "Renée")
        # already-correct text that can't be Latin-1 encoded, or isn't valid UTF-8 bytes, is kept
        self.assertEqual(_unmojibake("already 😂"), "already 😂")
        self.assertEqual(_unmojibake("café"), "café")
        self.assertIsNone(_unmojibake(None))

    def test_folder_merges_files_and_sorts_oldest_first(self):
        msgs = load_instagram(FOLDER)
        self.assertEqual(
            [(m.author, m.text) for m in msgs],
            [
                ("Jordan", "first day of the semester!!! 🔥"),
                ("Maya", "omw 😭"),
                ("Jordan", ""),
                ("Renée", "who is coming to the café tonight?"),
                ("Jordan", "anyone up for breakfast?"),
                ("Renée", "WAKE UP THEO 😂😂"),
                ("Theo", "ok ok I'm up"),
                ("Maya", ""),
            ],
        )
        self.assertEqual(msgs, sorted(msgs, key=lambda m: m.ts))
        self.assertEqual(msgs[0].ts, datetime.fromtimestamp(1788285600))

    def test_reactions_media_and_notices(self):
        msgs = load_instagram(FOLDER)
        by_text = {m.text: m for m in msgs if m.text}
        self.assertEqual(by_text["omw 😭"].reactions, {"😂": 2})
        self.assertEqual(by_text["ok ok I'm up"].reactions, {"❤️": 1})
        self.assertEqual(by_text["anyone up for breakfast?"].attachments, 1)  # video plus text
        photo, share = msgs[2], msgs[7]
        self.assertEqual((photo.author, photo.attachments), ("Jordan", 1))
        # "Maya sent an attachment." is a placeholder, not something she typed
        self.assertEqual((share.author, share.text, share.attachments), ("Maya", "", 1))
        texts = [m.text for m in msgs]
        self.assertNotIn("Liked a message", texts)
        self.assertNotIn("this is unsent", texts)

    def test_single_file_and_load_dispatch(self):
        one = parse_instagram((FOLDER / "message_2.json").read_text(encoding="utf-8"))
        self.assertEqual(len(one), 4)
        self.assertEqual(len(load(FOLDER / "message_2.json", "instagram")), 4)
        self.assertEqual(len(load(FOLDER, "instagram")), 8)

    def test_files_are_ordered_by_number_not_name(self):
        base = json.loads((FOLDER / "message_2.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            for n in (1, 2, 10):
                part = dict(base, messages=[{"sender_name": "Maya", "timestamp_ms": 1788285600000 + n, "content": f"part {n}"}])
                (Path(tmp) / f"message_{n}.json").write_text(json.dumps(part), encoding="utf-8")
            self.assertEqual([m.text for m in load_instagram(tmp)], ["part 1", "part 2", "part 10"])

    def test_empty_folder_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            load_instagram(tmp)

    def test_cli_on_the_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [sys.executable, "-m", "wrapped.cli", str(FOLDER), "--format", "instagram",
                 "--optin", "Maya,Jordan,Renée,Theo", "--out", tmp, "--no-render"],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("8 messages", proc.stdout)
            result = json.loads((Path(tmp) / "stats.json").read_text(encoding="utf-8"))
            self.assertIn("Renée", result["members"])


if __name__ == "__main__":
    unittest.main()
