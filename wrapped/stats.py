"""Group totals and awards. Everything here is deterministic.

Every award is a dict:
    {title, key, winner, value_text, detail, receipt: {author, ts, text}, [context]}
where ``receipt`` is a real message from the input that shows the award is true.

Consent: only names in ``opted_in`` may win, be quoted, or be named. Everyone
else counts toward group totals as "someone", and their names are scrubbed
from any quoted text.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

from .model import Message

SOMEONE = "someone"
LEFT_ON_READ_WINDOW = timedelta(minutes=60)
REPLY_WINDOW = timedelta(minutes=60)  # a reply slower than this isn't a "reply"
BURST_GAP = timedelta(minutes=30)
OMW_FOLLOWUP_CAP = timedelta(hours=3)
MIN_SAMPLE = 3  # messages needed for an average/median to count
MIN_REPLIES = 5
MIN_WORD_COUNT = 5
LATE_NIGHT = range(1, 5)  # 1:00-4:59 AM

OMW = re.compile(r"\b(omw|on my way|otw)\b", re.IGNORECASE)
WORD = re.compile(r"[a-z]+(?:'[a-z]+)*")
URL = re.compile(r"https?://\S+")
EMOJI = re.compile(
    "[\U0001F300-\U0001F3FA\U0001F400-\U0001FAFF\U0001F000-\U0001F2FF☀-➿⭐⭕❣❤]"
)

STOPWORDS = frozenset(
    """a about above after again against all am an and any are as at be because been before being below
    between both but by can could did do does doing down during each few for from further had has have
    having he her here hers herself him himself his how i if in into is it its itself just me more most my
    myself no nor not now of off on once only or other our ours ourselves out over own same she should so
    some such than that the their theirs them themselves then there these they this those through to too
    under until up very was we were what when where which while who whom why will with would you your yours
    yourself yourselves im ive ill id youre dont cant wont isnt didnt doesnt thats whats theres""".split()
)
# Words every group chat overuses; they are not this group's word.
CHAT_SLANG = frozenset(
    """lol lmao lmfao rofl omg omfg idk idc tbh ngl imo imho fr frfr smh btw brb ttyl jk wtf wth irl
    omw otw bruh bro bros dude dudes yall y'all gonna wanna gotta kinda sorta lemme gimme yeah yea yep yup
    nah nope okay okk okayy haha hahaha hahahaha lmaooo lmaoo hehe xd ugh ughh hmm hmmm mhm aww awww yay
    yess yesss yessss noo nooo noooo sooo soooo sooooo pls plz thx ty np rn tmrw tmr tn ppl bc cuz cause
    sus lowkey highkey deadass vibe vibes vibing slay slaps bet cap mid literally fam goat goated""".split()
)


# ----------------------------------------------------------------- helpers ---

@lru_cache(maxsize=1)
def english_ranks() -> dict[str, int]:
    """word -> rank (1 = most common) from the bundled list."""
    ranks: dict[str, int] = {}
    path = Path(__file__).with_name("data") / "english_top.txt"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            continue
        for word in line.split():
            ranks.setdefault(word.lower(), len(ranks) + 1)
    return ranks


def words(text: str) -> list[str]:
    return WORD.findall(URL.sub(" ", text.lower().replace("’", "'")))


def is_question(text: str) -> bool:
    return text.rstrip().endswith("?")


def is_hype(text: str) -> bool:
    if "!!!" in text:
        return True
    letters = [c for c in text if c.isalpha()]
    return len(letters) >= 4 and all(c.isupper() for c in letters)


def fmt_duration(delta: timedelta) -> str:
    s = int(delta.total_seconds())
    if s < 60:
        return f"{s} second{'s' if s != 1 else ''}"
    if s < 3600:
        m = round(s / 60)
        return f"{m} min"
    h, m = divmod(round(s / 60), 60)
    if h >= 48:
        d, h = divmod(h, 24)
        return f"{d} days {h} h" if h else f"{d} days"
    return f"{h} h {m} min" if m else f"{h} h"


def fmt_hour(hour: int) -> str:
    return f"{(hour % 12) or 12} {'AM' if hour < 12 else 'PM'}"


class Redactor:
    """Replaces the names of people who did not opt in with "someone"."""

    def __init__(self, hidden_names: set[str]):
        tokens = set()
        for name in hidden_names:
            tokens.add(name)
            tokens.update(t for t in re.split(r"\s+", name) if len(t) >= 3)
        self._pattern = (
            re.compile(r"@?\b(" + "|".join(sorted(map(re.escape, tokens), key=len, reverse=True)) + r")\b", re.IGNORECASE)
            if tokens
            else None
        )

    def __call__(self, text: str) -> str:
        return self._pattern.sub(SOMEONE, text) if self._pattern else text


# ----------------------------------------------------------------- compute ---

def match_optins(authors, opted_in) -> set[str]:
    """The authors the opt-in names pick out. An exact name always matches; a
    different case matches only when exactly one author has it, so one
    person's consent never passes to a case-variant of their name."""
    authors = sorted(authors)
    named = set()
    for n in sorted(n.strip() for n in (opted_in or ()) if n.strip()):
        if n in authors:
            named.add(n)
            continue
        same = [a for a in authors if a.casefold() == n.casefold()]
        if len(same) == 1:
            named.add(same[0])
    return named


def hidden_names(messages: list[Message], named) -> set[str]:
    """Every name the people who didn't opt in go by: their author name, or,
    for an author keyed by id, the names in its aliases (the id is never shown)."""
    aliases: dict[str, set[str]] = defaultdict(set)
    for m in messages:
        aliases[m.author].update(m.aliases)
    return {n for a, names in aliases.items() if a not in named for n in (names or {a})}


def name_words(messages: list[Message], named) -> set[str]:
    """The lowercase words in everyone's names, opted in or not."""
    return {w for n in set(named) | hidden_names(messages, named) for w in words(n)}


def compute(messages: list[Message], opted_in: set[str] | None = None) -> dict:
    messages = sorted(messages, key=lambda m: m.ts)
    authors = {m.author for m in messages}
    named = match_optins(authors, opted_in)
    redact = Redactor(hidden_names(messages, named))
    ctx = _Context(messages, named, redact)

    awards = [
        a
        for a in (
            _main_character(ctx),
            _novelist(ctx),
            _three_am(ctx),
            _omw(ctx),
            _left_on_read(ctx),
            _hype(ctx),
            _speed_demon(ctx),
            _ghost(ctx),
            _emoji(ctx),
            _group_word(ctx),
            _busiest_day(ctx),
        )
        if a
    ]
    return {"group": _group_totals(ctx), "members": sorted(named), "awards": awards}


class _Context:
    def __init__(self, messages, named, redact):
        self.messages = messages
        self.named = named
        self.redact = redact
        self.by_author: dict[str, list[Message]] = defaultdict(list)
        for m in messages:
            self.by_author[m.author].append(m)

    def mine(self, author: str, with_text=True) -> list[Message]:
        return [m for m in self.by_author[author] if m.text.strip() or not with_text]

    def receipt(self, m: Message) -> dict:
        return {"author": m.author, "ts": m.ts.isoformat(), "text": self.redact(m.text)}


def _pick(scores: dict[str, float], lowest=False) -> str | None:
    """Winner by score; ties go to the alphabetically first name."""
    if not scores:
        return None
    sign = 1 if lowest else -1
    return min(scores, key=lambda name: (sign * scores[name], name.casefold(), name))


def _secs(ts: datetime) -> float:
    return (ts - datetime.min).total_seconds()


def _first_by(items, key):
    """The item with the largest key; ties go to the earliest message."""
    return max(items, key=lambda m: (key(m), -_secs(m.ts)))


def _award(ctx, key, title, winner, value_text, receipt_msg, detail="", context_msg=None):
    a = {
        "key": key,
        "title": title,
        "winner": winner,
        "value_text": value_text,
        "detail": detail,
        "receipt": ctx.receipt(receipt_msg),
    }
    if context_msg is not None:
        a["context"] = ctx.receipt(context_msg)
    return a


def _group_totals(ctx: _Context) -> dict:
    msgs = ctx.messages
    if not msgs:
        return {"messages": 0}
    hours = Counter(m.ts.hour for m in msgs)
    weekdays = Counter(m.ts.strftime("%A") for m in msgs)
    busiest_hour = min(hours, key=lambda h: (-hours[h], h))
    busiest_weekday = min(weekdays, key=lambda d: (-weekdays[d], d))
    share = Counter(m.author if m.author in ctx.named else SOMEONE for m in msgs)
    return {
        "messages": len(msgs),
        "words": sum(len(words(m.text)) for m in msgs),
        "media": sum(m.attachments for m in msgs),
        "people": len(ctx.by_author),
        "first": msgs[0].ts.isoformat(),
        "last": msgs[-1].ts.isoformat(),
        "days": (msgs[-1].ts.date() - msgs[0].ts.date()).days + 1,
        "busiest_hour": fmt_hour(busiest_hour),
        "busiest_hour_messages": hours[busiest_hour],
        "busiest_weekday": busiest_weekday,
        "busiest_weekday_messages": weekdays[busiest_weekday],
        "share": dict(sorted(share.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


# ------------------------------------------------------------------ awards ---

def _main_character(ctx):
    scores = {a: len(ctx.by_author[a]) for a in ctx.named if ctx.by_author[a]}
    w = _pick(scores)
    if not w:
        return None
    # Receipt: the opening line of their longest uninterrupted run in one
    # sitting (no gap over 30 minutes).
    best_start, best_len, start, run, prev = None, 0, None, 0, None
    for m in ctx.messages:
        if m.author == w:
            if run == 0 or m.ts - prev.ts > BURST_GAP:
                start, run = m, 0
            run += 1
            if run > best_len and start.text.strip():
                best_start, best_len = start, run
        else:
            run = 0
        prev = m
    if best_start is None:
        return None
    pct = round(100 * scores[w] / len(ctx.messages))
    return _award(
        ctx, "main_character", "Main Character", w,
        f"{scores[w]:,} messages, {pct}% of the whole chat",
        best_start, detail=f"Once sent {best_len} in a row without anyone answering. It started like this:",
    )


def _novelist(ctx):
    avgs = {}
    for a in ctx.named:
        texts = ctx.mine(a)
        if len(texts) >= MIN_SAMPLE:
            avgs[a] = sum(len(words(m.text)) for m in texts) / len(texts)
    w = _pick(avgs)
    if not w:
        return None
    longest = _first_by(ctx.mine(w), lambda m: len(words(m.text)))
    rest = [m for m in ctx.messages if m.author != w and m.text.strip()]
    rest_avg = sum(len(words(m.text)) for m in rest) / len(rest) if rest else 0
    return _award(
        ctx, "novelist", "The Novelist", w,
        f"{avgs[w]:.1f} words per message on average; everyone else: {rest_avg:.1f}",
        longest, detail=f"Longest message: {len(words(longest.text))} words.",
    )


def _three_am(ctx):
    late = {a: [m for m in ctx.mine(a) if m.ts.hour in LATE_NIGHT] for a in ctx.named}
    w = _pick({a: len(v) for a, v in late.items() if v})
    if not w:
        return None
    best = _first_by(late[w], lambda m: len(words(m.text)))
    return _award(
        ctx, "three_am", "3 AM Philosopher", w,
        f"{len(late[w])} messages sent between 1 and 5 AM",
        best, detail="A highlight from the small hours:",
    )


def _omw(ctx):
    omws = {a: [m for m in ctx.mine(a) if OMW.search(m.text)] for a in ctx.named}
    w = _pick({a: len(v) for a, v in omws.items() if v})
    if not w:
        return None
    # Receipt: the "omw" they took longest to follow up on (within 3 hours).
    own = ctx.by_author[w]
    nxt = {id(a): b for a, b in zip(own, own[1:])}

    def wait(m):
        n = nxt.get(id(m))
        gap = (n.ts - m.ts) if n else timedelta(0)
        return gap if gap <= OMW_FOLLOWUP_CAP else timedelta(0)

    best = _first_by(omws[w], wait)
    detail = f"Their next message came {fmt_duration(wait(best))} later." if wait(best) else ""
    n = len(omws[w])
    return _award(
        ctx, "omw", "“omw” (they were not)", w,
        f"said “omw” {n} time{'s' if n != 1 else ''}",
        best, detail=detail,
    )


def _silence_after(ctx, i: int) -> timedelta | None:
    """Time until someone other than the sender speaks, or None if nobody ever does."""
    m = ctx.messages[i]
    for later in ctx.messages[i + 1:]:
        if later.author != m.author:
            return later.ts - m.ts
    return None


def _left_on_read(ctx):
    ignored: dict[str, list[tuple[Message, timedelta | None]]] = defaultdict(list)
    for i, m in enumerate(ctx.messages):
        if m.author in ctx.named and is_question(m.text):
            gap = _silence_after(ctx, i)
            if gap is None or gap > LEFT_ON_READ_WINDOW:
                ignored[m.author].append((m, gap))
    w = _pick({a: len(v) for a, v in ignored.items()})
    if not w:
        return None
    forever = timedelta(days=100000)
    m, gap = max(ignored[w], key=lambda mg: (mg[1] or forever, -_secs(mg[0].ts)))
    detail = "Nobody ever answered." if gap is None else f"First reply from anyone: {fmt_duration(gap)} later."
    n = len(ignored[w])
    return _award(
        ctx, "left_on_read", "Left On Read", w,
        f"{n} question{'s' if n != 1 else ''} nobody answered within an hour",
        m, detail=detail,
    )


def _hype(ctx):
    hype = {a: [m for m in ctx.mine(a) if is_hype(m.text)] for a in ctx.named}
    w = _pick({a: len(v) for a, v in hype.items() if v})
    if not w:
        return None
    best = _first_by(hype[w], lambda m: sum(c.isupper() for c in m.text) + m.text.count("!"))
    return _award(
        ctx, "hype", "Hype Machine", w,
        f"{len(hype[w])} messages in ALL CAPS or with “!!!”",
        best, detail="Exhibit A:",
    )


def _speed_demon(ctx):
    replies: dict[str, list[tuple[timedelta, Message, Message]]] = defaultdict(list)
    for prev, m in zip(ctx.messages, ctx.messages[1:]):
        gap = m.ts - prev.ts
        if m.author != prev.author and gap <= REPLY_WINDOW and m.author in ctx.named and m.text.strip():
            replies[m.author].append((gap, m, prev))
    medians = {
        a: statistics.median(g.total_seconds() for g, _, _ in r)
        for a, r in replies.items()
        if len(r) >= MIN_REPLIES
    }
    w = _pick(medians, lowest=True)
    if not w:
        return None
    # Receipt: their fastest reply, preferring one to a named member (context is shown).
    gap, reply, prev = min(
        replies[w], key=lambda t: (t[2].author not in ctx.named or not t[2].text.strip(), t[0], t[1].ts)
    )
    context = prev if prev.author in ctx.named and prev.text.strip() else None
    return _award(
        ctx, "speed_demon", "Speed Demon", w,
        f"median reply time: {fmt_duration(timedelta(seconds=medians[w]))}",
        reply, detail=f"Replied in {fmt_duration(gap)}.", context_msg=context,
    )


def _ghost(ctx):
    counts = {a: len(ctx.by_author[a]) for a in ctx.named if ctx.mine(a)}
    if len(counts) < 2:
        return None
    w = _pick(counts, lowest=True)
    shortest = min(ctx.mine(w), key=lambda m: (len(m.text.strip()), m.ts))
    total = len(ctx.messages)
    return _award(
        ctx, "ghost", "The Ghost", w,
        f"only {counts[w]:,} messages, {100 * counts[w] / total:.0f}% of the chat",
        shortest, detail="Their most efficient contribution:",
    )


def _emoji(ctx):
    overall = Counter(e for m in ctx.messages for e in EMOJI.findall(m.text))
    if not overall:
        return None
    top = min(overall, key=lambda e: (-overall[e], e))
    per = {a: sum(m.text.count(top) for m in ctx.mine(a)) for a in ctx.named}
    w = _pick({a: n for a, n in per.items() if n})
    if not w:
        return None
    best = _first_by([m for m in ctx.mine(w) if top in m.text], lambda m: m.text.count(top))
    return _award(
        ctx, "emoji", "Emoji of the Semester", w,
        f"{top} used {overall[top]:,} times"
        + (f", every single one by {w}" if per[w] == overall[top] else f", {per[w]:,} of them by {w}"),
        best, detail=f"{w} loves it most:",
    ) | {"emoji": top}


def _group_word(ctx):
    name_tokens = name_words(ctx.messages, ctx.named)
    counts: Counter[str] = Counter()
    users: dict[str, set[str]] = defaultdict(set)
    total = 0
    for m in ctx.messages:
        ws = words(m.text)
        total += len(ws)
        for word in ws:
            word = word.removesuffix("'s")
            counts[word] += 1
            users[word].add(m.author)
    ranks = english_ranks()
    unknown_rank = len(ranks) + 1
    candidates = {
        word: n * ranks.get(word, unknown_rank)
        for word, n in counts.items()
        if n >= MIN_WORD_COUNT
        and len(word) >= 4
        and len(users[word]) >= 2
        and "'" not in word
        and word not in STOPWORDS
        and word not in CHAT_SLANG
        and word not in name_tokens
        and not OMW.fullmatch(word)
    }
    if not candidates:
        return None
    word = min(candidates, key=lambda wd: (-candidates[wd], wd))
    pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
    per = {a: sum(len(pattern.findall(m.text)) for m in ctx.mine(a)) for a in ctx.named}
    w = _pick({a: n for a, n in per.items() if n})
    if not w:
        return None
    first = min((m for m in ctx.mine(w) if pattern.search(m.text)), key=lambda m: m.ts)
    if word in ranks:
        # Zipf estimate of how often English uses this word, per word of text.
        harmonic = sum(1 / r for r in range(1, unknown_rank))
        expected = 1 / (ranks[word] * harmonic)
        detail = f"About {counts[word] / total / expected:,.0f}x more than everyday English (estimated)."
    else:
        detail = f"Not even in the top {len(ranks):,} English words."
    return _award(
        ctx, "group_word", "Group Word", w,
        f"“{word}”, said {counts[word]:,} times; {w} said it most ({per[w]:,})",
        first, detail=detail + f" {w}’s first time:",
    ) | {"word": word}


def _busiest_day(ctx):
    by_day: dict = defaultdict(list)
    for m in ctx.messages:
        by_day[m.ts.date()].append(m)
    if not by_day:
        return None
    day = min(by_day, key=lambda d: (-len(by_day[d]), d))
    bursts, cur = [], [by_day[day][0]]
    for prev, m in zip(by_day[day], by_day[day][1:]):
        if m.ts - prev.ts > BURST_GAP:
            bursts.append(cur)
            cur = []
        cur.append(m)
    bursts.append(cur)
    biggest = max(bursts, key=lambda b: (len(b), -_secs(b[0].ts)))
    opener = next((m for m in biggest if m.author in ctx.named and m.text.strip()), None)
    if opener is None:
        opener = next((m for m in by_day[day] if m.author in ctx.named and m.text.strip()), None)
    if opener is None:
        return None
    return _award(
        ctx, "busiest_day", "Busiest Day", opener.author,
        f"{day.strftime('%A, %B')} {day.day}: {len(by_day[day]):,} messages",
        opener, detail=f"The biggest burst ({len(biggest)} messages) started with {opener.author}:",
    ) | {"date": day.isoformat()}
