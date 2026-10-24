# Group Chat Wrapped — plan (Cubbie Hackathon, Track 3: Group Chat Assistant)

Team hercules · written 2026-10-24.

## The moment

The semester is ending and the group chat has 14,000 messages. Who said "omw" the most while very much
not on the way? Who sends paragraphs at 3 AM? Who leaves everyone on read? Spotify Wrapped, for your
group chat.

## What it does

Invite the bot, type `/wrapped`, and it posts a short story of 8–10 vertical slides into the chat: the
group's stats and a set of awards, each **backed by the receipt** (a quoted message, with its date).
Funny because it's true.

Why a group would invite it: it's instant, shareable entertainment, and it gives the chat a moment
at the end of a semester.

## Awards (deterministic, every one cites its evidence)

| Award | Rule |
|---|---|
| Main Character | most messages |
| The Novelist | longest average message |
| 3 AM Philosopher | most messages sent 1–5 AM |
| "omw" (they were not) | most "omw / on my way / otw" |
| Left On Read | most questions with no reply within an hour |
| Hype Machine | most messages with "!!!" or all caps |
| Speed Demon | fastest median reply time |
| The Ghost | fewest messages (only among opted-in members) |
| Emoji of the Semester | most-used emoji, and who loves it most |
| Group Word | the word this group uses far more than normal English |
| Busiest Day | the date with the most messages, plus the message that started it |

## Consent and privacy

- Only members who opted in (`/wrapped optin`) are named. Everyone else counts toward group totals as
  "someone" and never gets an award or a quote.
- Only stats and the quoted receipts leave the bot. No message text is stored after a run.
- The repo ships with an **invented** demo chat; never a real one.

## Architecture (Python 3.12)

```text
group-chat-wrapped/
├── wrapped/
│   ├── model.py        Message(ts, author, text, reply_to, reactions, attachments)
│   ├── importers.py    WhatsApp .txt export, Discord channel JSON (DiscordChatExporter shape), plain CSV
│   ├── stats.py        All awards and totals, each returning {winner, value, receipt}
│   ├── slides.py       Builds the slide deck as one HTML page (1080x1920 slides)
│   ├── render.py       Renders slides to PNG with Playwright WebKit (no Chromium)
│   ├── cli.py          python -m wrapped.cli chat.txt --out out/   (works with no accounts)
│   └── platforms/      (phase 3) discord_bot.py (/wrapped optin|optout|run), imessage.py (one group, via chat.db
│                       and Messages); Instagram is an importer (--format instagram)
├── demo/demo-chat.txt  invented 4-person friend group, one semester, ~2,000 messages (generated)
└── tests/
```

## Platforms (phase 3)

- **Discord:** the "hercules" bot. `/wrapped optin`, then `/wrapped` reads the channel's history and posts
  the slides and the MP4 in the channel. Token from the Keychain.
- **iMessage:** a Mac bridge reads one group chat from `~/Library/Messages/chat.db` (read-only, on the Mac
  of a member of that chat). When someone in the group types "wrapped", it posts the slides back into the
  group through the Messages app. Opt-in is by members replying "optin" in the group. It sends only into the
  chat it was asked to run in.
- **Instagram:** no bot can join an Instagram group chat (Meta's messaging API covers business accounts
  in one-to-one threads only). So Wrapped reads Instagram's own chat export ("Download your information",
  JSON, `messages/inbox/<chat>/message_1.json`). The slides are 1080x1920, which is the Stories size, ready
  to post.

## Phases

1. **Importers + stats + CLI (no accounts).** Tests for each importer, each award rule, the tie-breaks,
   and the opt-in filter (a non-opted member never appears by name or quote).
2. **Slides + render.** A good-looking vertical deck (same visual standard as the Track 1 video),
   rendered to PNGs and a short MP4.
3. **Platforms.** Discord bot, iMessage bridge, Instagram export importer. Tested against fakes; no live sends during the build.
4. **Video + submit.**

## Done when

- `python -m unittest discover -s tests` passes offline.
- `python -m wrapped.cli demo/demo-chat.txt --out out/` writes the slides, and every award on a slide
  has a receipt that really is in the chat.
- (Phase 3) `/wrapped` in a test Discord server posts the deck.

## Optional later

AI-written award captions, as a flourish only. The awards themselves stay computed, so a caption can't
invent a fact.
