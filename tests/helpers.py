from datetime import datetime

from wrapped.model import Message
from wrapped.stats import Redactor, hidden_names


def M(author, when, text="", **kw):
    """M("Ana", "2026-09-01 10:00", "hi")"""
    return Message(ts=datetime.fromisoformat(when), author=author, text=text, **kw)


def chat(*rows):
    return [M(*r) for r in rows]


def assert_receipts_real(test, result, messages):
    """Every receipt (and context bubble) is a real message from the input,
    up to the redaction of non-opted names, and one the Redactor could quote."""
    members = set(result["members"])
    redact = Redactor(hidden_names(messages, members), members)
    real = {(m.author, m.ts.isoformat(), redact(m.text)) for m in messages if redact.quotable(m.text)}
    for award in result["awards"]:
        for key in ("receipt", "context"):
            if key in award:
                r = award[key]
                test.assertIn((r["author"], r["ts"], r["text"]), real, award["title"])
                test.assertIn(r["author"], result["members"], award["title"])
