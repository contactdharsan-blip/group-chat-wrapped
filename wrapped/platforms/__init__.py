"""Chat platforms: each one turns its history into Messages and runs the same pipeline as the CLI."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .. import render, slides, stats
from ..model import Message


@dataclass
class Story:
    result: dict
    html: Path
    pngs: list[Path] = field(default_factory=list)
    video: Path | None = None


def make_story(messages: list[Message], opted: set[str], out: Path, name: str, render_media: bool = True) -> Story:
    """stats.json + slides.html, then (render_media) PNGs and an MP4.

    Raises ValueError for an empty chat, and render.RenderUnavailable when the
    PNGs can't be made. The MP4 is best effort: without ffmpeg the story is
    still the PNGs."""
    if not messages:
        raise ValueError("no messages to wrap")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    result = stats.compute(messages, opted)
    (out / "stats.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    html = out / "slides.html"
    html.write_text(slides.build_html(result, name), encoding="utf-8")
    story = Story(result=result, html=html)
    if not render_media:
        return story
    story.pngs, _ = render.render_pngs(html, out)
    try:
        story.video = render.make_video(story.pngs, out / "wrapped.mp4")
    except render.RenderUnavailable:
        story.video = None
    return story


def config_dir() -> Path:
    """Where the platforms keep their only state (opt-ins, last seen row)."""
    return Path.home() / ".config" / "group-chat-wrapped"
