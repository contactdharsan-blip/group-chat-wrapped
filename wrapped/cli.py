"""python -m wrapped.cli <chat file> --format whatsapp|discord|csv|instagram --optin "A,B,C" --out out/"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import captions, importers, profiles, render, slides, stats


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wrapped", description="Spotify Wrapped for a group chat.")
    p.add_argument("chat", help="chat export file")
    p.add_argument("--format", choices=sorted(importers.PARSERS), default="whatsapp")
    p.add_argument("--optin", default="", help="comma-separated names of members who agreed to be named")
    p.add_argument("--out", default="out", help="output directory")
    p.add_argument("--name", default="Group Chat Wrapped", help="chat name for the title slide")
    p.add_argument("--no-render", action="store_true", help="skip the PNG and MP4 step")
    p.add_argument("--claude", action="store_true",
                   help="write award captions with Claude into captions.json (templates otherwise; needs the Keychain key)")
    args = p.parse_args(argv)

    opted = {n.strip() for n in args.optin.split(",") if n.strip()}
    messages = importers.load(args.chat, args.format)
    result = stats.compute(messages, opted)
    unknown = sorted(n for n in opted if n.casefold() not in {m.author.casefold() for m in messages})
    if unknown:
        print(f"note: opted-in names not found in the chat: {', '.join(unknown)}", file=sys.stderr)
    if not result["members"]:
        print("note: nobody opted in, so there are no awards (pass --optin \"Name,Name\")", file=sys.stderr)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "stats.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    client = captions.make_client() if args.claude else None
    if args.claude and client is None:
        print("note: no anthropic SDK or no Keychain key, so captions are templates", file=sys.stderr)
    caps = captions.captions(result["awards"], profiles.build(messages, result), client)
    (out / "captions.json").write_text(json.dumps(caps, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    html = out / "slides.html"
    html.write_text(slides.build_html(result, args.name), encoding="utf-8")
    print(f"{len(messages):,} messages, {len(result['awards'])} awards -> {out}/stats.json, {html}")

    if args.no_render:
        return 0
    try:
        pngs, warnings = render.render_pngs(html, out)
        for w in warnings:
            print(f"warning: content inside the overlay zone: {w}", file=sys.stderr)
        video = render.make_video(pngs, out / "wrapped.mp4")
    except render.RenderUnavailable as e:
        print(f"render skipped: {e}", file=sys.stderr)
        return 2
    print(f"{len(pngs)} slides -> {out}/slide-01.png .. {pngs[-1].name}, {video}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
