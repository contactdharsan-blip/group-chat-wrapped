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
