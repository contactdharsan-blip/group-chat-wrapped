"""The one record every importer produces."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    ts: datetime  # naive, wall-clock time as the export shows it
    author: str
    text: str
    reply_to: str | None = None
    reactions: dict[str, int] = field(default_factory=dict)
    attachments: int = 0
    # Other names this author goes by, when ``author`` is an id key that is
    # never shown (Discord's "user:<id>" for people who didn't opt in). Used
    # only to scrub those names from quoted text.
    aliases: tuple[str, ...] = ()
