"""Render slides.html to PNGs (Playwright WebKit, via Node) and stitch an MP4 (ffmpeg)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

# Default: the playwright-core already installed for the sibling demo (used read-only).
DEFAULT_PLAYWRIGHT_CORE = "/Users/Dharsan/Downloads/free-food-demo/node_modules/playwright-core"
SCRIPT = Path(__file__).with_name("render_slides.cjs")
SECONDS_PER_SLIDE = 2.5
FADE = 0.3


class RenderUnavailable(RuntimeError):
    pass


def playwright_core() -> str:
    return os.environ.get("PLAYWRIGHT_CORE", DEFAULT_PLAYWRIGHT_CORE)


def can_render() -> bool:
    return bool(shutil.which("node")) and Path(playwright_core()).is_dir()


def render_pngs(html: Path, out_dir: Path) -> tuple[list[Path], list[str]]:
    """Returns the PNG paths and any safe-zone violations WebKit measured."""
    if not can_render():
        raise RenderUnavailable(f"needs node and playwright-core at {playwright_core()} (set PLAYWRIGHT_CORE)")
    for old in out_dir.glob("slide-*.png"):
        old.unlink()
    env = {**os.environ, "PLAYWRIGHT_CORE": playwright_core()}
    proc = subprocess.run(
        ["node", str(SCRIPT), str(html), str(out_dir)], env=env, capture_output=True, text=True, timeout=300
    )
    if proc.returncode != 0:
        raise RenderUnavailable(f"WebKit render failed:\n{proc.stderr.strip()}")
    pngs = [Path(line) for line in proc.stdout.split("\n") if line.strip()]
    warnings = [line.removeprefix("SAFE-ZONE ") for line in proc.stderr.splitlines() if line.startswith("SAFE-ZONE ")]
    return pngs, warnings


def make_video(pngs: list[Path], out: Path, seconds: float = SECONDS_PER_SLIDE, fade: float = FADE) -> Path:
    if not shutil.which("ffmpeg"):
        raise RenderUnavailable("ffmpeg is not on PATH")
    cmd = ["ffmpeg", "-loglevel", "error", "-y"]
    for png in pngs:
        cmd += ["-loop", "1", "-framerate", "30", "-t", f"{seconds}", "-i", str(png)]
    if len(pngs) == 1:
        graph, last = "[0:v]format=yuv420p[v]", "[v]"
    else:
        parts, prev = [], "[0:v]"
        for k in range(1, len(pngs)):
            label = f"[x{k}]"
            parts.append(f"{prev}[{k}:v]xfade=transition=fade:duration={fade}:offset={k * (seconds - fade):.3f}{label}")
            prev = label
        parts.append(f"{prev}format=yuv420p[v]")
        graph, last = ";".join(parts), "[v]"
    cmd += ["-filter_complex", graph, "-map", last, "-r", "30", "-c:v", "libx264", "-movflags", "+faststart", str(out)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise RenderUnavailable(f"ffmpeg failed:\n{proc.stderr.strip()}")
    return out
