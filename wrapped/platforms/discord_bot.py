"""The Discord bot: /wrapped optin, /wrapped optout, /wrapped run.

    .venv/bin/python -m wrapped.platforms.discord_bot [--guild <server id>]

Everything above build_bot() is plain Python over duck-typed Discord objects, so
it is tested with fakes and needs neither discord.py nor the network. discord.py
is imported only inside build_bot() and main().

The only state is the opt-in file (discord-optins.json in the config dir). A run
works in a temporary folder that is deleted once the slides are posted.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import AsyncIterable, Awaitable, Callable
from pathlib import Path

from .. import render
from ..model import Message
from . import config_dir, make_story

HISTORY_LIMIT = 20_000  # newest messages read per run
PROGRESS_EVERY = 1_000
FILES_PER_MESSAGE = 10  # Discord's attachment limit per message
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # Discord's upload limit without Nitro or boosts


class OptinStore:
    """{channel id: {user id: name at opt-in}} in one JSON file."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else config_dir() / "discord-optins.json"

    def _load(self) -> dict[str, dict[str, str]]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}

    def _save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)

    def names(self, channel_id) -> dict[str, str]:
        return self._load().get(str(channel_id), {})

    def opt_in(self, channel_id, user_id, name: str) -> None:
        data = self._load()
        data.setdefault(str(channel_id), {})[str(user_id)] = name
        self._save(data)

    def opt_out(self, channel_id, user_id) -> bool:
        data = self._load()
        removed = data.get(str(channel_id), {}).pop(str(user_id), None) is not None
        if removed:
            self._save(data)
        return removed


def to_message(dm, names: dict[str, str]) -> Message | None:
    """A discord.Message as a Message, or None for bots and system notices.

    Opted-in authors keep the name they opted in under, so a later nickname
    change doesn't drop them; everyone else gets their current display name
    (and the pipeline shows them only as "someone")."""
    if getattr(dm.author, "bot", False):
        return None
    if getattr(dm.type, "name", "default") not in ("default", "reply"):
        return None  # joins, pins, boosts, thread notices
    ref = getattr(dm, "reference", None)
    reactions: dict[str, int] = {}
    for r in getattr(dm, "reactions", None) or []:
        key = str(r.emoji)
        reactions[key] = reactions.get(key, 0) + int(r.count)
    return Message(
        # created_at is aware UTC; the pipeline wants this machine's wall clock.
        ts=dm.created_at.astimezone().replace(tzinfo=None),
        author=names.get(str(dm.author.id), dm.author.display_name),
        text=dm.content or "",
        reply_to=str(ref.message_id) if ref is not None and getattr(ref, "message_id", None) else None,
        reactions=reactions,
        attachments=len(getattr(dm, "attachments", None) or []),
    )


async def read_history(history: AsyncIterable, names: dict[str, str],
                       progress: Callable[[int], Awaitable[None]] | None = None) -> list[Message]:
    messages, seen = [], 0
    async for dm in history:
        seen += 1
        m = to_message(dm, names)
        if m is not None:
            messages.append(m)
        if progress and seen % PROGRESS_EVERY == 0:
            await progress(seen)
    return sorted(messages, key=lambda m: m.ts)


def chunks(items: list, size: int = FILES_PER_MESSAGE) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items), size)]


Send = Callable[[list[Path]], Awaitable[None]]


class Handlers:
    """What each slash command does, given plain ids, a channel and a send callback."""

    def __init__(self, store: OptinStore, *, limit: int = HISTORY_LIMIT, render_media: bool = True,
                 story_maker=make_story):
        self.store, self.limit, self.render_media, self.story_maker = store, limit, render_media, story_maker

    def optin(self, channel_id, user_id, name: str) -> str:
        self.store.opt_in(channel_id, user_id, name)
        return f"You're in as **{name}**. Wrapped can now name you and quote you in this channel."

    def optout(self, channel_id, user_id) -> str:
        if self.store.opt_out(channel_id, user_id):
            return "You're out. Wrapped will count you only as \"someone\" from now on."
        return "You weren't opted in here."

    async def run(self, channel, chat_name: str, send: Send,
                  progress: Callable[[int], Awaitable[None]] | None = None) -> str:
        names = self.store.names(channel.id)
        if not names:
            return "Nobody in this channel has opted in yet. Run `/wrapped optin` first."
        history = channel.history(limit=self.limit, oldest_first=False)
        messages = await read_history(history, names, progress)
        if not messages:
            return "There are no messages to wrap in this channel."
        with tempfile.TemporaryDirectory(prefix="wrapped-discord-") as tmp:
            try:
                story = await asyncio.to_thread(
                    self.story_maker, messages, set(names.values()), Path(tmp), chat_name, self.render_media
                )
            except render.RenderUnavailable as e:
                return f"Couldn't render the slides on the bot's machine: {e}"
            for group in chunks(story.pngs):
                await send(group)
            note = ""
            if story.video is not None:
                if story.video.stat().st_size <= MAX_UPLOAD_BYTES:
                    await send([story.video])
                else:
                    note = " The video was over Discord's 10 MB limit, so only the slides were posted."
        capped = " (the newest ones; the cap was reached)" if len(messages) >= self.limit else ""
        return (f"Wrapped {len(messages):,} messages{capped}: {len(story.result['awards'])} awards "
                f"for {len(story.result['members'])} opted-in members.{note}")


def build_bot(handlers: Handlers, guild_id: int | None = None):
    """The discord.py client with the /wrapped command group. Does not connect."""
    import discord
    from discord import app_commands

    intents = discord.Intents.default()
    intents.message_content = True  # privileged: switch it on in the Developer Portal too
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)
    group = app_commands.Group(name="wrapped", description="Spotify Wrapped for this channel")

    @group.command(name="optin", description="Let Wrapped name and quote you in this channel")
    async def optin(interaction: discord.Interaction):
        text = handlers.optin(interaction.channel_id, interaction.user.id, interaction.user.display_name)
        await interaction.response.send_message(text, ephemeral=True)

    @group.command(name="optout", description="Stop Wrapped naming or quoting you in this channel")
    async def optout(interaction: discord.Interaction):
        await interaction.response.send_message(handlers.optout(interaction.channel_id, interaction.user.id),
                                                ephemeral=True)

    @group.command(name="run", description="Read this channel's history and post its Wrapped")
    async def run(interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        status = await interaction.followup.send("Reading this channel's history...", wait=True)

        async def progress(n: int):
            await status.edit(content=f"Reading this channel's history... {n:,} messages so far")

        async def send(paths: list[Path]):
            await interaction.channel.send(files=[discord.File(p) for p in paths])

        name = getattr(interaction.channel, "name", None) or "Group Chat Wrapped"
        summary = await handlers.run(interaction.channel, f"#{name}", send, progress)
        await status.edit(content=summary)

    tree.add_command(group)

    async def setup_hook():  # once per start, not on every reconnect like on_ready
        if guild_id:  # a test server: the commands appear at once
            guild = discord.Object(id=guild_id)
            tree.copy_global_to(guild=guild)
            await tree.sync(guild=guild)
        else:  # everywhere: Discord can take up to an hour to show them
            await tree.sync()

    client.setup_hook = setup_hook

    @client.event
    async def on_ready():
        print(f"logged in as {client.user}; /wrapped is registered", file=sys.stderr)

    return client, tree


def keychain_token() -> str:
    """The bot token, read from the Keychain into memory. Never printed, logged or written."""
    proc = subprocess.run(
        ["security", "find-generic-password", "-a", "hercules", "-s", "discord-bot-token", "-w"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise SystemExit("no Keychain item 'discord-bot-token' for account 'hercules' (see README, Platforms)")
    return proc.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wrapped-discord", description="Run the Group Chat Wrapped Discord bot.")
    p.add_argument("--guild", type=int, help="server id to register the commands in at once (else global)")
    p.add_argument("--limit", type=int, default=HISTORY_LIMIT, help="newest messages read per run")
    args = p.parse_args(argv)
    try:
        import discord  # noqa: F401
    except ImportError:
        print("discord.py is not installed; see README, Platforms > Discord", file=sys.stderr)
        return 1
    client, _ = build_bot(Handlers(OptinStore(), limit=args.limit), args.guild)
    client.run(keychain_token())
    return 0


if __name__ == "__main__":
    sys.exit(main())
