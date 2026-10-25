"""Build the story as one self-contained HTML page of 1080x1920 slides.

Each slide is a <section class="slide" id="slide-NN">. Content sits inside a
safe box that stays clear of the bottom 400 px and the right 168 px, where
TikTok / Reels / Stories draw their own buttons and captions.
"""

from __future__ import annotations

from datetime import datetime
from html import escape

WIDTH, HEIGHT = 1080, 1920
SAFE_TOP, SAFE_LEFT, SAFE_RIGHT, SAFE_BOTTOM = 150, 96, 168, 400

# (background, text) pairs: Apple system colours, one per slide.
PALETTE = {
    "main_character": ("#FF2D55", "#FFFFFF"),
    "novelist": ("#5856D6", "#FFFFFF"),
    "three_am": ("#1C1C3A", "#FFFFFF"),
    "omw": ("#FF9500", "#1D1D1F"),
    "left_on_read": ("#8E8E93", "#FFFFFF"),
    "hype": ("#FFCC00", "#1D1D1F"),
    "speed_demon": ("#34C759", "#1D1D1F"),
    "ghost": ("#E5E5EA", "#1D1D1F"),
    "emoji": ("#00C7BE", "#1D1D1F"),
    "group_word": ("#AF52DE", "#FFFFFF"),
    "busiest_day": ("#FF3B30", "#FFFFFF"),
}
DEFAULT = ("#007AFF", "#FFFFFF")

KICKERS = {
    "main_character": "Said the most",
    "novelist": "Wrote the most per message",
    "three_am": "Awake when nobody else was",
    "omw": "Was always on the way",
    "left_on_read": "Asked into the void",
    "hype": "Never used an indoor voice",
    "speed_demon": "Replied before you finished typing",
    "ghost": "Said the least",
    "emoji": "Sent one emoji more than any other",
    "group_word": "Your group’s word",
    "busiest_day": "The day the chat lost it",
}

CSS = f"""
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ background: #0B0B0C; }}
body {{
  font-family: -apple-system, "SF Pro Display", BlinkMacSystemFont, "Helvetica Neue", Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  display: flex; flex-direction: column; align-items: center; gap: 48px; padding: 48px 0;
}}
.slide {{
  position: relative; width: {WIDTH}px; height: {HEIGHT}px; overflow: hidden;
  background: var(--bg); color: var(--fg);
}}
.safe {{
  position: absolute; top: {SAFE_TOP}px; left: {SAFE_LEFT}px; right: {SAFE_RIGHT}px; bottom: {SAFE_BOTTOM}px;
  display: flex; flex-direction: column;
}}
.count {{ font-size: 34px; font-weight: 600; letter-spacing: 0.02em; opacity: 0.7; }}
.kicker {{ font-size: 44px; font-weight: 600; margin-top: 28px; opacity: 0.85; }}
.title {{ font-size: 104px; font-weight: 800; line-height: 1.0; letter-spacing: -0.035em; margin-top: 14px; }}
.winner {{ font-size: 190px; font-weight: 800; line-height: 0.95; letter-spacing: -0.045em; margin-top: 64px; }}
.hero {{ font-size: 300px; line-height: 1; margin-top: 56px; }}
.value {{ font-size: 54px; font-weight: 600; line-height: 1.2; margin-top: 30px; letter-spacing: -0.01em; }}
.detail {{ font-size: 40px; font-weight: 500; line-height: 1.3; margin-top: auto; padding-top: 40px; opacity: 0.85; }}
.thread {{ display: flex; flex-direction: column; gap: 18px; margin-top: 24px; }}
.bubble {{
  align-self: flex-start; max-width: 100%;
  background: #FFFFFF; color: #1D1D1F; border-radius: 44px; padding: 30px 40px 28px;
}}
.bubble.reply {{ align-self: flex-end; background: #1D1D1F; color: #FFFFFF; }}
.bubble .who {{ font-size: 32px; font-weight: 700; opacity: 0.6; margin-bottom: 8px; }}
.bubble .text {{
  font-size: var(--fs, 40px); line-height: 1.32; white-space: pre-wrap; overflow-wrap: anywhere;
  display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: var(--lines, 9); overflow: hidden;
}}
.bubble .when {{ font-size: 30px; font-weight: 500; opacity: 0.55; margin-top: 14px; }}
.stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 56px 40px; margin-top: 80px; }}
.stat .n {{ font-size: 112px; font-weight: 800; letter-spacing: -0.04em; line-height: 1; }}
.stat .l {{ font-size: 34px; font-weight: 600; opacity: 0.7; margin-top: 10px; }}
.share {{ margin-top: auto; display: flex; flex-direction: column; gap: 22px; }}
.row {{ display: grid; grid-template-columns: 220px 1fr 120px; align-items: center; gap: 20px; font-size: 34px; font-weight: 600; }}
.bar {{ height: 26px; border-radius: 13px; background: rgba(255,255,255,0.14); overflow: hidden; }}
.bar i {{ display: block; height: 100%; border-radius: 13px; background: var(--accent); }}
.row .c {{ text-align: right; opacity: 0.8; font-variant-numeric: tabular-nums; }}
.big {{ font-size: 150px; font-weight: 800; line-height: 0.95; letter-spacing: -0.045em; margin-top: auto; }}
.sub {{ font-size: 46px; font-weight: 600; line-height: 1.25; margin-top: 36px; opacity: 0.9; }}
.fine {{ font-size: 30px; font-weight: 500; line-height: 1.35; margin-top: 48px; opacity: 0.6; }}
.accent {{ color: var(--accent); }}
"""


def _when(iso: str) -> str:
    ts = datetime.fromisoformat(iso)
    return f"{ts.strftime('%a, %b')} {ts.day}, {ts.year} · {(ts.hour % 12) or 12}:{ts.minute:02d} {'AM' if ts.hour < 12 else 'PM'}"


def _bubble(receipt: dict, reply: bool = False) -> str:
    text = receipt["text"]
    n = len(text)
    fs, lines = (60, 6) if n <= 90 else (48, 8) if n <= 200 else (36, 10) if n <= 420 else (30, 11)
    cls = "bubble reply" if reply else "bubble"
    return (
        f'<div class="{cls}"><div class="who">{escape(receipt["author"])}</div>'
        f'<div class="text" style="--fs:{fs}px;--lines:{lines}">{escape(text)}</div>'
        f'<div class="when">{escape(_when(receipt["ts"]))}</div></div>'
    )


def _headline(text: str) -> str:
    """The giant name/word, shrunk so a long one still fits the safe width on one line."""
    usable = WIDTH - SAFE_LEFT - SAFE_RIGHT
    size = min(190, int(usable / (0.58 * max(len(text), 1))))
    return f'<div class="winner" style="font-size:{size}px">{escape(text)}</div>'


def _slide(n: int, bg: str, fg: str, body: str, accent: str | None = None) -> str:
    style = f"--bg:{bg};--fg:{fg};--accent:{accent or fg}"
    return f'<section class="slide" id="slide-{n:02d}" style="{style}"><div class="safe">{body}</div></section>'


def _date_range(group: dict) -> str:
    if "first" not in group:
        return ""
    a, b = datetime.fromisoformat(group["first"]), datetime.fromisoformat(group["last"])
    left = f"{a.strftime('%b')} {a.day}" + (f", {a.year}" if a.year != b.year else "")
    return f"{left} – {b.strftime('%b')} {b.day}, {b.year}"


def _title_slide(n: int, name: str, group: dict) -> str:
    body = (
        f'<div class="count">{escape(name)}</div>'
        '<div class="big">Your group chat, <span class="accent">wrapped.</span></div>'
        f'<div class="sub">{escape(_date_range(group))}{"<br>" if "first" in group else ""}{group["messages"]:,} messages</div>'
        '<div class="fine">Only friends who opted in are named. Every award quotes a real message.</div>'
    )
    return _slide(n, "#000000", "#FFFFFF", body, accent="#FF2D55")


def _totals_slide(n: int, group: dict) -> str:
    stats = [
        (f'{group["messages"]:,}', "messages"),
        (f'{group["words"]:,}', "words"),
        (f'{group["media"]:,}', "photos, stickers & files"),
        (f'{group["days"]:,}', "days"),
        (group["busiest_hour"], "busiest hour"),
        (group["busiest_weekday"] + "s", "busiest day of the week"),
    ]
    cells = "".join(f'<div class="stat"><div class="n">{escape(v)}</div><div class="l">{escape(l)}</div></div>' for v, l in stats)
    top = max(group["share"].values())
    rows = "".join(
        f'<div class="row"><span>{escape(who)}</span><span class="bar"><i style="width:{100 * c / top:.1f}%"></i></span>'
        f'<span class="c">{c:,}</span></div>'
        for who, c in list(group["share"].items())[:6]
    )
    body = (
        '<div class="count">The semester in numbers</div>'
        '<div class="title">You did <span class="accent">not</span> stop talking.</div>'
        f'<div class="stats">{cells}</div>'
        f'<div class="share">{rows}</div>'
    )
    return _slide(n, "#000000", "#FFFFFF", body, accent="#0A84FF")


def _award_slide(n: int, i: int, total: int, award: dict) -> str:
    bg, fg = PALETTE.get(award["key"], DEFAULT)
    value = f'<div class="value">{escape(award["value_text"])}</div>'
    if award["key"] == "emoji":
        hero = f'<div class="hero">{escape(award["emoji"])}</div>{value}'
    elif award["key"] == "group_word":
        hero = _headline(f'“{award["word"]}”') + value
    elif award["key"] == "busiest_day":
        day = datetime.fromisoformat(award["date"])
        hero = _headline(f"{day.strftime('%b')} {day.day}") + value
    else:
        hero = _headline(award["winner"]) + value
    thread = ""
    if "context" in award:
        thread += _bubble(award["context"])
    thread += _bubble(award["receipt"], reply="context" in award)
    body = (
        f'<div class="count">Award {i} of {total}</div>'
        f'<div class="title">{escape(award["title"])}</div>'
        f'<div class="kicker">{escape(KICKERS.get(award["key"], ""))}</div>'
        f"{hero}"
        f'<div class="detail">{escape(award["detail"])}</div>'
        f'<div class="thread">{thread}</div>'
    )
    return _slide(n, bg, fg, body)


def _closing_slide(n: int, result: dict) -> str:
    names = result["members"]
    who = ", ".join(names[:-1]) + f" and {names[-1]}" if len(names) > 1 else (names[0] if names else "everyone")
    body = (
        '<div class="count">That’s a wrap</div>'
        f'<div class="big">Same chat, <span class="accent">next semester.</span></div>'
        f'<div class="sub">Starring {escape(who)}.</div>'
        '<div class="fine">Every number here is counted from the chat, and every quote is a real message.</div>'
    )
    return _slide(n, "#000000", "#FFFFFF", body, accent="#30D158")


def build_html(result: dict, chat_name: str = "Group Chat Wrapped") -> str:
    awards = result["awards"]
    slides = [_title_slide(1, chat_name, result["group"])]
    if result["group"].get("messages"):
        slides.append(_totals_slide(len(slides) + 1, result["group"]))
    for i, award in enumerate(awards, 1):
        slides.append(_award_slide(len(slides) + 1, i, len(awards), award))
    slides.append(_closing_slide(len(slides) + 1, result))
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(chat_name)} · Wrapped</title><style>{CSS}</style></head>"
        f"<body>{''.join(slides)}</body></html>\n"
    )
