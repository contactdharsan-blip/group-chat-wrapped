import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from wrapped import render

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "demo" / "demo-chat.txt"
OPTIN = "Maya,Jordan,Priya,Theo"


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "wrapped.cli", str(DEMO), "--format", "whatsapp", "--optin", OPTIN, *args],
        cwd=ROOT, capture_output=True, text=True, timeout=600,
    )


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


class CliTests(unittest.TestCase):
    def test_end_to_end_without_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = run_cli("--out", tmp, "--no-render")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads((Path(tmp) / "stats.json").read_text(encoding="utf-8"))
            self.assertEqual(len(result["awards"]), 11)
            html = (Path(tmp) / "slides.html").read_text(encoding="utf-8")
            self.assertEqual(html.count('class="slide"'), 14)

    def test_partial_optin_hides_the_rest(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [sys.executable, "-m", "wrapped.cli", str(DEMO), "--optin", "Maya,Priya", "--out", tmp, "--no-render"],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            for name in ("stats.json", "slides.html"):
                text = (Path(tmp) / name).read_text(encoding="utf-8").lower()
                self.assertNotIn("jordan", text, name)
                self.assertNotIn("theo", text, name)

    def test_export_with_no_messages_says_so(self):
        with tempfile.TemporaryDirectory() as tmp:
            chat = Path(tmp) / "empty.txt"
            chat.write_text("[9/1/26, 12:00:00 PM] Group: \u200eMessages and calls are end-to-end encrypted.\n"
                            "[9/1/26, 12:00:05 PM] Ana added Ben\n", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "-m", "wrapped.cli", str(chat), "--optin", "Ana", "--out", str(Path(tmp) / "out"),
                 "--no-render"],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertIn("no messages found", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)
            self.assertFalse((Path(tmp) / "out").exists())

    @unittest.skipUnless(render.can_render(), "node + playwright-core WebKit not available")
    def test_end_to_end_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = run_cli("--out", tmp, "--name", "Floor 4 Survivors")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertNotIn("overlay zone", proc.stderr)
            pngs = sorted(Path(tmp).glob("slide-*.png"))
            self.assertEqual(len(pngs), 14)
            for png in pngs:
                self.assertEqual(png_size(png), (1080, 1920), png.name)
            video = Path(tmp) / "wrapped.mp4"
            self.assertGreater(video.stat().st_size, 10_000)
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                capture_output=True, text=True,
            )
            if probe.returncode == 0:
                expected = 14 * render.SECONDS_PER_SLIDE - 13 * render.FADE
                self.assertAlmostEqual(float(probe.stdout), expected, delta=0.2)


if __name__ == "__main__":
    unittest.main()
