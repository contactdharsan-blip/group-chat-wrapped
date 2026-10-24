# Group Chat Wrapped

Spotify Wrapped for your group chat. Cubbie Hackathon, Track 3 (group chat assistant).

## The moment

The semester is over and the group chat has thousands of messages. Who said "omw" the most while
very much not on the way? Who sends paragraphs at 3 AM? Whose questions get left on read?

## What it does

It reads a chat export and makes a short vertical story: the group's numbers, then eleven awards
(Main Character, The Novelist, 3 AM Philosopher, "omw" (they were not), Left On Read, Hype Machine,
Speed Demon, The Ghost, Emoji of the Semester, Group Word, Busiest Day). Each award comes with a
**receipt**, a real quoted message with its date, so you can check it's true.

The awards are counted, not generated, and ties are broken the same way every time. The rules are in
`PLAN.md` and `wrapped/stats.py`.

Output, in `out/`:

- `slides.html`: every slide on one self-contained page (1080x1920 each)
- `slide-01.png` …: one PNG per slide, rendered in WebKit
- `wrapped.mp4`: the slides with a quick crossfade, about 2.5 s each
- `stats.json`: the numbers and awards behind the slides

Content stays out of the bottom 350 px and right 120 px, where TikTok, Reels and Stories draw
their buttons. The renderer measures every slide and warns if anything crosses that line.

## Consent and privacy

- Only people named in `--optin` can win, be quoted, or be named. Everyone else still counts in
  the group totals, as "someone", and their names are replaced with "someone" in any quoted text.
- It runs locally, with no network calls and no accounts. Nothing is uploaded.
- The repo ships an **invented** demo chat (`demo/demo-chat.txt`, made by
  `demo/make_demo_chat.py`). Never commit a real chat.

## Run it on a WhatsApp export

In WhatsApp, open the chat, then **Export chat → Without media**, and save the `.txt`.

```sh
python3 -m wrapped.cli "WhatsApp Chat with Friends.txt" --format whatsapp \
    --optin "Maya,Jordan,Priya,Theo" --name "Floor 4 Survivors" --out out/
```

The names must match how they appear in the export. Both export layouts work:
`[10/24/26, 9:41:03 PM] Name: text` (iPhone) and `10/24/26, 21:41 - Name: text` (Android).
Dates are read month-first unless the file has a day above 12 in the first position.

The other formats: `--format discord` for a DiscordChatExporter JSON file, and `--format csv` for a
CSV with a `timestamp,author,text` header.

Use `--no-render` to make only `stats.json` and `slides.html`.

The demo:

```sh
python3 -m wrapped.cli demo/demo-chat.txt --format whatsapp --optin "Maya,Jordan,Priya,Theo" \
    --name "Floor 4 Survivors" --out out/
```

## Requirements

- Python 3.12+, standard library only.
- To render PNGs and the MP4: Node, `playwright-core` with its WebKit build, and `ffmpeg` on PATH.
  Set `PLAYWRIGHT_CORE` to the path of a `playwright-core` install. The default is a path on the
  author's machine (`wrapped/render.py`). Rendering uses WebKit only, never Chromium.

## Tests

```sh
python3 -m unittest discover -s tests
```

They run offline. The full-render test skips itself when Node or WebKit isn't available.
`tests/test_demo_story.py` locks the demo's story: each award goes to the friend it was written for.

## Notes

- Group Word compares the chat against a bundled list of about 2,900 common English words
  (`wrapped/data/english_top.txt`). The list was written by hand for this repo, and its ranks are
  approximate.
- The 1–5 AM award uses the clock time shown in the export.
