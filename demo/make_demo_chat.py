"""Generate demo/demo-chat.txt: an INVENTED four-friend college group chat.

Everyone and everything in it is made up. It is written as an iOS WhatsApp
export (bracketed timestamps, narrow no-break space before AM/PM, left-to-right
marks on system lines and media) so the demo exercises the real parser.

The cast, scripted so each award has a clear winner:
  Maya    talks the most, replies instantly, ALL CAPS hype
  Jordan  "omw" (is not), lives on the skull emoji
  Priya   writes paragraphs at 3 AM
  Theo    asks questions nobody answers; quietest; named the dining hall cat Bingus

Run:  python3 demo/make_demo_chat.py   (deterministic: seeded RNG)
"""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from pathlib import Path

GROUP = "Floor 4 Survivors"
MAYA, JORDAN, PRIYA, THEO = "Maya", "Jordan", "Priya", "Theo"
CAST = [MAYA, JORDAN, PRIYA, THEO]
START, END = date(2026, 8, 19), date(2026, 12, 12)
NNBSP, LRM = " ", "‎"
IMAGE, STICKER = f"{LRM}image omitted", f"{LRM}sticker omitted"
SKULL, SOB = "\U0001F480", "\U0001F62D"

rng = random.Random(2026)
events: list[tuple[datetime, str, str]] = []


def say(t: datetime, who: str, text: str) -> None:
    events.append((t, who, text))


def wait(minutes: float):
    return ("WAIT", minutes)


def reply_gap(who: str, prev: str | None) -> timedelta:
    if prev == who:
        return timedelta(seconds=rng.randint(4, 40))
    lo, hi = {MAYA: (2, 25), JORDAN: (35, 240), PRIYA: (45, 420), THEO: (60, 600)}[who]
    return timedelta(seconds=rng.randint(lo, hi))


def run(start: datetime, script) -> datetime:
    t, prev = start, None
    for item in script:
        if item[0] == "WAIT":
            t += timedelta(minutes=item[1], seconds=rng.randint(0, 50))
            continue
        who, text = item
        if prev is not None or t != start:
            t += reply_gap(who, prev) if prev is not None else timedelta(0)
        say(t, who, text)
        prev = who
    return t


def at(day: date, hh: int, mm: int = 0, ss: int | None = None) -> datetime:
    return datetime.combine(day, time(hh, mm, rng.randint(0, 59) if ss is None else ss))


BINGUS_NAMED = date(2026, 8, 22)  # the day after Theo names him


def pop(pool: list, day: date | None = None):
    """Take a random item out of a pool so it is never reused."""
    options = [i for i, x in enumerate(pool) if day is None or knows_bingus(x, day)]
    return pool.pop(rng.choice(options))


def knows_bingus(text: str, day: date) -> bool:
    """Nobody mentions Bingus before Theo names him."""
    return day >= BINGUS_NAMED or "bingus" not in text.lower()


# --------------------------------------------------------------- content ---

HALLS = ["Hartley", "the dining hall", "Hartley", "North Commons"]

DINNER_ASK = [
    "dinner at {hall} at {t}?",
    "{hall} at {t}? I'm starving",
    "who's down for {hall} at {t}",
    "dinner. {hall}. {t}. be there",
    "food at {t}? {hall}",
]
DINNER_HERE = [
    "here, got the booth by the window",
    "here",
    "we're at the usual table",
    "here. it's taco night!!",
    "got a table near the ice cream machine",
]
JORDAN_OMW = [
    "omw", "omw!!", "omw 2 min", "literally omw", "omw just putting shoes on", "otw",
    "on my way", "omw for real this time", "omw " + SKULL, "omw just finishing an episode",
    "omw I promise", "omw!! save me a seat", "omw, which hall again",
]
WHERE_IS_JORDAN = [
    "jordan where are you",
    "jordan it's been 20 min",
    "is jordan coming or",
    "jordan you said omw 25 minutes ago",
    "update on jordan?",
    "we're on dessert jordan",
]
JORDAN_STILL = ["omw!!", "2 min", "ok actually leaving now", "the elevator is slow I swear", "omw omw omw",
                "ok I'm outside which door", "I'm here!! where'd you go", "ran into someone from bio sorry"]
DONE_EATING = ["we're literally done eating", "we're leaving", "bringing you a cookie, hurry",
               "we waited. we're going back now", "you missed taco night"]

THEO_ALONE = [
    "does anyone know if the dining hall takes guest swipes on sundays?",
    "is it normal for the lounge microwave to smell like that?",
    "who took my charger from the lounge?",
    "does anyone want to split a costco membership?",
    "is the bio quiz open note?",
    "did anyone else get the email about the fire drill?",
    "has anyone seen my left shoe?",
    "is it weird to bring a crockpot to the library?",
    "can someone explain what \"synergy\" means? the rubric says it four times",
    "do we need to print the lab report or just submit it?",
    "anyone want to go to the planetarium show friday?",
    "is the laundry room on 2 working again?",
    "what time does the gym close on saturdays?",
    "does anyone have a stapler I can borrow?",
    "did the RA say quiet hours start at 10 or 11?",
    "anyone else think the new dining hall pasta tastes like a candle?",
    "is it too late to switch out of 8am stats?",
    "how do you cook rice without a rice cooker?",
    "do you guys think Bingus has a home?",
    "anyone want to start a book club?",
    "what's the wifi password for the library again?",
    "does anyone know a good place to get a haircut near campus?",
    "should I get a bike or is that a lot?",
    "is anyone going to the career fair?",
    "has anyone done the chem pre-lab yet?",
    "can you get a parking ticket on a scooter?",
    "anyone know how to get a stain out of a hoodie?",
    "is the bookstore open on sunday?",
    "anyone want to come to the club fair with me?",
    "do we have class on labor day?",
    "is it bad that I've eaten cereal for dinner four nights in a row?",
    "anyone want to get boba later?",
    "does the shuttle go to the target?",
    "is it normal to have 3 midterms in one week?",
    "anyone else's radiator making a ghost noise?",
    "should I bring a jacket to the game or is it warm?",
    "how many hours of sleep is technically enough?",
    "does anyone want my extra meal swipes?",
    "is Bingus allowed inside or is that a health code thing?",
    "anyone want to study for the final together?",
    "does anyone know when move-out is?",
    "can I put a mini fridge on top of another mini fridge?",
    "anyone want to learn to juggle with me?",
    "is the vending machine on 4 eating anyone else's dollars?",
]
THEO_THANKSGIVING = "happy thanksgiving! is anyone else's family asking about their grades or is it just mine?"

PRIYA_3AM = [
    "ok so I've been thinking. if Bingus lives outside the dining hall, and the dining hall belongs to the university, then technically Bingus is enrolled here. he has better attendance than I do in orgo. he has never once missed a meal. he is thriving. what if we are the ones who are lost and Bingus is the only one who actually understands college",
    "can't sleep. does anyone else feel like the first week of college is three months long and also fifteen minutes long. I met forty people today and I remember one name and it was the guy who sold me a lanyard",
    "random thought but every time I microwave popcorn in the lounge I think about how the smell is going to outlive me. in a hundred years someone will walk down this hallway and think. someone here made a choice",
    "I just realized I've been pronouncing \"syllabus\" wrong in my head for my entire life and nobody corrected me. I have been living a lie. I'm going to read every syllabus out loud tomorrow as an apology",
    "still up. the library at 2 am is a different universe. there's a guy on the third floor who has been building a tower out of highlighters for an hour and honestly it's the most productive thing I've seen all week",
    "do you ever look at the ceiling of your dorm and think about all the other people who looked at this exact ceiling. one of them probably also had an orgo exam at 9. we are connected through the ceiling",
    "update: I have read the same paragraph about enzymes eleven times. I now know nothing about enzymes but I know a lot about the font. it's a nice font. I would trust this font with my life",
    "hot take at 3 am. the dining hall waffle machine is the most important building on campus. not the library. not the student center. the waffle machine. it brings people together. it beeps when it's done. it believes in us",
    "it's 3am and I just learned that octopuses have three hearts and I've been sitting here thinking about how I can barely handle one",
    "I think the group project is going to be ok. I made a spreadsheet. the spreadsheet has a tab called \"feelings\". no one else has opened it but it's there for them",
    "you know what nobody tells you about college. it's mostly walking. I have walked so much. my calves have their own personalities now",
    "I wrote a whole essay draft and then realized the prompt said \"compare\" and I only \"contrasted\". this is the worst thing that has ever happened to anyone. I'm going to sleep. I'm not going to sleep",
    "the radiator just made a noise like it was trying to tell me something. I think it said \"drop the class\". I'm not dropping the class. but I heard it",
    "ok this is going to sound crazy but I think Bingus recognizes me now. he looked at me today. like really looked. we have an understanding. I bring him nothing and he forgives me",
    "thinking about how the four of us met because the fire alarm went off at 2am on move-in week and we all stood outside in our pajamas and Maya was the only one who brought a snack. that was the moment. that was when I knew",
    "night thought: what if midterms are just a test of how many times you can say \"ok I'll start at 9\" and then start at 11:40",
    "I'm reorganizing my notes by color. green is things I understand. red is things I don't. it's all red. it's a very beautiful red",
    "can't sleep because I keep thinking about the guy in lecture who asked a question that was actually just a story about his uncle. respect. I want that confidence",
    "the vending machine on our floor ate my dollar again and I'm choosing to see it as a donation to the building. we are all part of the building",
    "still awake. I've decided that when I graduate I'm going to write a book called \"things I learned at 3 am\" and it's going to be 400 pages long and chapter one is just about the waffle machine",
    "I think finals are a group hallucination. we all agreed they're happening so now they're happening. if we all just stopped believing in them",
    "I just reread my notes from week one and past me wrote \"this class seems easy\" and I want to go back in time and gently hold her hand",
    "okay. the laundry room has a lost and found and I think it's been the same three socks since august. they are a family now. they are thriving",
    "I love you guys. that's it. that's the message. it's 3 am and I'm being honest. go to sleep. I'm not going to",
]
PRIYA_EPIC = (
    "Ok I have to tell you all about the new dining hall menu because I have Thoughts. First, the stir fry station.\n"
    "They have changed the sauce. They didn't tell anyone. There was no announcement, no email, no small sign, nothing. "
    "It used to be sweet and a little spicy and now it's just brown. Brown is not a flavor. Second, the dessert section "
    "now has a \"chef's special\" every night and tonight it was a pudding that I can only describe as confident. "
    "It knew what it was. I respect it but I didn't enjoy it. Third, and this is the important one, they moved the "
    "cereal. The cereal has been in the same corner since the day we moved in and now it's next to the salad bar like "
    "it's trying to be healthy. It's not healthy. It's cereal. Let it be cereal.\n"
    "Anyway I wrote all of this in the feedback box and signed it \"a concerned resident of floor 4\" and I feel "
    "like I made a difference today"
)
MORNING_AFTER = {
    MAYA: ["PRIYA ITS 3AM", "PRIYA GO TO SLEEP", "why are you like this " + SOB, "I woke up to an essay", "ok but this is so real"],
    JORDAN: [SKULL * 3, "priya what", "nah this one is crazy " + SKULL, "the 3am thoughts are back " + SKULL, "philosophy hour again"],
    THEO: ["this is beautiful honestly", "did you sleep at all", "I agree about the waffle machine"],
}

OPENERS = [
    (MAYA, "GUYS"),
    (MAYA, "ok who wants to hear the dumbest thing that happened in stats"),
    (MAYA, "my roommate just set off the smoke alarm making toast"),
    (MAYA, "WAIT did everyone see the email about the free pizza"),
    (MAYA, "I just saw our professor at the grocery store and panicked and hid behind the bananas"),
    (MAYA, "someone in my lecture brought a full rotisserie chicken"),
    (JORDAN, "who stole the lounge couch cushions " + SKULL),
    (JORDAN, "bro the elevator just stopped between floors for a full minute"),
    (JORDAN, "my alarm didn't go off and I woke up at 11:58 for a 12:00 " + SKULL),
    (JORDAN, "the guy across the hall is practicing the trumpet again"),
    (JORDAN, "just got the stats grade back " + SKULL + SKULL),
    (PRIYA, "the library has a nap room. I'm never leaving"),
    (PRIYA, "I just got called on in lecture and said \"present\" like it was roll call"),
    (PRIYA, "my bio lab partner named our fruit flies"),
    (PRIYA, "reminder that the floor meeting is tonight"),
    (THEO, "Bingus is sitting on the dining hall steps again"),
    (THEO, "Bingus update: he has a new spot by the bike rack"),
    (THEO, "saw Bingus chase a leaf for five minutes. he lost"),
    (THEO, "someone put a tiny sweater on Bingus"),
    (THEO, "Bingus walked into my lecture today. the professor let him stay"),
    (MAYA, "BINGUS IS ON THE CAMPUS INSTAGRAM"),
    (JORDAN, "bingus just stole a fry from a guy on the quad " + SKULL),
    (PRIYA, "Bingus sat with me while I studied. best study partner I've had"),
]
REACT = {
    MAYA: ["NO WAY", "WAIT WHAT", "STOPPP", "LMAOOO", "omg", "I'm screaming", "NOT AGAIN", "this is the best day of my life",
           "I NEED DETAILS", "HAHAHA", "iconic", "obsessed", "why is this so funny " + SOB, IMAGE, "BINGUS!!!"],
    JORDAN: [SKULL, SKULL * 3, "nah that's crazy", "bro", "real", "can't make this up " + SKULL, "lmao",
             "that's insane", "w", STICKER, "bingus supremacy"],
    PRIYA: ["honestly valid", "this is so real " + SOB, "I need to sit down", "the drama", "protect him at all costs",
            "ok this made my day", SOB, "I'm putting this in my diary"],
    THEO: ["lol", "huh", "wait really", "nice", "bingus would never", "classic", "oh no", "k"],
}

PROJECT_RANT = [
    "ok I need to rant",
    "so our group project has five people",
    "one of them has not opened the doc",
    "not once",
    "it's been three weeks",
    "today he messaged the group chat \"hey guys what's the project about\"",
    "THE PRESENTATION IS FRIDAY",
    "I made him a slide that just says \"thank you for coming\"",
    "he said \"perfect\"",
    "I'm going to lie down",
]


# ------------------------------------------------------------- episodes ---

recent_openers: list = []


def ep_chatter(start: datetime) -> datetime:
    day = start.date()
    opener = rng.choice([o for o in OPENERS if knows_bingus(o[1], day) and o not in recent_openers])
    recent_openers[:] = (recent_openers + [opener])[-12:]  # no repeats within 12 conversations
    script, prev = [opener], opener[0]
    for _ in range(rng.randint(2, 6)):
        who = rng.choices([w for w in CAST if w != prev], weights=[{MAYA: 10, JORDAN: 5, PRIYA: 5, THEO: 2}[w] for w in CAST if w != prev])[0]
        script.append((who, rng.choice([r for r in REACT[who] if knows_bingus(r, day)])))
        prev = who
    return run(start, script)


def ep_dinner(start: datetime, hall: str | None = None) -> datetime:
    hall = hall or rng.choice(HALLS)
    meal = start + timedelta(hours=1)
    t_str = f"{(meal.hour % 12) or 12}{':30' if meal.minute >= 30 else ''}"
    asker = rng.choice([MAYA, PRIYA, MAYA, THEO])
    others = [w for w in (MAYA, PRIYA, THEO) if w != asker]
    script = [
        (asker, rng.choice(DINNER_ASK).format(hall=hall, t=t_str)),
        (others[0], rng.choice(["YES", "in", "I'm in", "yesss"])),
        (JORDAN, rng.choice(["in", "down", "yes I'm coming"])),
        wait(rng.randint(45, 55)),
        (rng.choice([MAYA, PRIYA]), rng.choice(DINNER_HERE)),
        wait(rng.randint(1, 4)),
        (JORDAN, rng.choice(JORDAN_OMW)),
        wait(rng.randint(12, 20)),
        (rng.choice([MAYA, THEO, PRIYA]), rng.choice(WHERE_IS_JORDAN)),
        (JORDAN, rng.choice(JORDAN_STILL)),
    ]
    if rng.random() < 0.6:
        script += [wait(rng.randint(10, 20)), (rng.choice([MAYA, PRIYA]), rng.choice(DONE_EATING))]
    script += [(JORDAN, rng.choice(["ok I'm here", "I'm here!! where'd you go", "here " + SKULL, "made it"]))]
    return run(start, script)


def ep_library(start: datetime) -> datetime:
    script = [
        (rng.choice([PRIYA, MAYA]), rng.choice(["library 3rd floor, we got the big table", "study room 204 if anyone wants to join",
                                               "library til close. saving seats"])),
        (THEO, "coming"),
        (JORDAN, rng.choice(["omw", "omw with snacks", "on my way after this episode"])),
        wait(rng.randint(30, 50)),
        (MAYA, rng.choice(["jordan the snacks?", "jordan we finished the chapter", "is jordan studying somewhere else"])),
        (JORDAN, rng.choice(["omw!!", "ok leaving now", "omw, got distracted"])),
        wait(rng.randint(8, 15)),
        (JORDAN, rng.choice(["here. what chapter are we on", "made it " + SKULL, "ok I'm here, who wants chips"])),
    ]
    return run(start, script)


def ep_3am(day: date) -> None:
    text = pop(PRIYA_3AM, day)
    if rng.random() < 0.3 and ". " in text:  # some paragraphs arrive with line breaks
        head, tail = text.split(". ", 1)
        text = f"{head}.\n{tail}"
    say(at(day, rng.choice([1, 2, 3, 3, 3, 4]), rng.randint(0, 59)), PRIYA, text)
    reacts = rng.sample([MAYA, JORDAN, THEO], k=rng.randint(1, 2))
    script = [(w, rng.choice(MORNING_AFTER[w])) for w in reacts]
    run(at(day, 8, rng.randint(5, 50)), script)


def ep_theo_alone(t: datetime) -> None:
    if THEO_ALONE:
        say(t, THEO, pop(THEO_ALONE, t.date()))


def ep_hype(start: datetime, lines) -> datetime:
    return run(start, lines)


# ---------------------------------------------------------- special days ---

def move_in(day: date) -> None:
    t = at(day, 14, 2, 11)
    say(t, GROUP, f"{LRM}Messages and calls are end-to-end encrypted. Only people in this chat can read, listen to, or share them.")
    say(t, GROUP, f"{LRM}Maya created group “{GROUP}”")
    say(t + timedelta(seconds=3), GROUP, f"{LRM}Maya added Jordan, Priya and Theo")
    run(t + timedelta(minutes=1), [
        (MAYA, "WELCOME TO FLOOR 4!!!"),
        (MAYA, "this is the official group chat. no pressure. but also it's official"),
        (PRIYA, "hi!! I'm in 412, the one with the plant"),
        (JORDAN, "yo"),
        (THEO, "hi, I'm Theo, 415. nice to meet everyone"),
        (MAYA, "dinner at 6 tonight??"),
        (JORDAN, "down"),
        (PRIYA, "yes please"),
        wait(230),
        (MAYA, "here!! we got a table"),
        (JORDAN, "omw"),
        wait(28),
        (THEO, "is jordan coming?"),
        (PRIYA, "he said omw 28 minutes ago"),
        (JORDAN, "omw!! got lost, this campus is huge"),
        wait(15),
        (JORDAN, "ok I'm here which table"),
        (MAYA, "the one where we're LEAVING"),
        (JORDAN, SKULL * 3),
    ])


def first_bingus(day: date) -> None:
    run(at(day, 19, 12), [
        (THEO, "there is a cat outside the dining hall and I have decided his name is Bingus"),
        (MAYA, "BINGUS"),
        (PRIYA, "Bingus is perfect"),
        (JORDAN, "bingus " + SKULL + SKULL),
        (THEO, IMAGE),
        (MAYA, "HE'S SO ROUND"),
        (THEO, "Bingus is the floor 4 mascot now. no takebacks"),
    ])


def football(day: date, big: bool) -> None:
    lines = [
        (MAYA, "GAME DAY GAME DAY GAME DAY"),
        (PRIYA, "I have my face paint ready"),
        (THEO, "should I bring a jacket?"),
        (MAYA, "BRING EVERYTHING"),
        (JORDAN, "meeting at the stadium gate at 6?"),
        (MAYA, "YES"),
    ]
    run(at(day, 11, 30), lines)
    # Jordan's legendary omw: the game starts without him.
    t = run(at(day, 17, 52), [
        (MAYA, "at the gate!! jordan said omw so we have like an hour"),
        (PRIYA, "here"),
        (THEO, "here"),
        (JORDAN, "omw!! don't go in without me"),
    ])
    in_game = [
        (MAYA, "we're going in jordan"),
        (PRIYA, "kickoff in 10"),
        (THEO, "do they let you in at halftime?"),
        (MAYA, "KICKOFF!!!"),
        (MAYA, "LETS GOOOOOO"),
        (PRIYA, "the band is so good"),
        (MAYA, IMAGE),
        (THEO, "Bingus would love this"),
        (MAYA, "FIRST DOWN!!"),
        (PRIYA, "jordan you are missing everything"),
    ]
    if big:
        in_game += [
            (MAYA, "TOUCHDOWN!!!"), (PRIYA, "AHHHH"), (THEO, "nice"), (MAYA, "I CAN'T HEAR ANYTHING"),
            (PRIYA, "the guy behind us is crying"), (MAYA, "SAME"), (THEO, "is it always this loud?"),
            (MAYA, "DEFENSE!!!"), (PRIYA, "DEFENSE"), (MAYA, IMAGE), (MAYA, "THAT WAS A FUMBLE??"),
            (PRIYA, "the refs are blind"), (THEO, "what's a fumble?"), (MAYA, "THEO"), (PRIYA, "oh theo " + SOB),
        ]
    run(t + timedelta(minutes=6), in_game)
    run(at(day, 19, 44), [
        (JORDAN, "ok who has my ticket"),
        (MAYA, "JORDAN ITS THE SECOND QUARTER"),
        (PRIYA, "he said omw an hour and a half ago " + SOB),
        (JORDAN, "I was on my way. spiritually"),
        (THEO, "classic"),
    ])
    if big:
        t = run(at(day, 20, 40), [
            (MAYA, "4TH QUARTER TIED"), (JORDAN, "IM HERE IM HERE"), (PRIYA, "I can't watch"), (MAYA, "WATCH"),
            (THEO, "this is very stressful"), (JORDAN, "COME ON"), (MAYA, "THIRD AND LONG"), (PRIYA, "please please please"),
            (MAYA, "HE CAUGHT IT"), (JORDAN, "NO WAY"), (MAYA, "FIELD GOAL TEAM IS OUT"), (PRIYA, "I'm holding Theo's arm"),
            (THEO, "she is holding my arm"), (MAYA, "IT'S GOOD!!!!!!"),
            (MAYA, "WE BEAT STATE!!! I AM NEVER SPEAKING AT A NORMAL VOLUME AGAIN!!!"),
            (JORDAN, SKULL * 4), (PRIYA, "I'm crying actual tears"), (THEO, "that was the best thing I've ever seen"),
            (MAYA, "STORMING THE FIELD"), (JORDAN, "WE'RE STORMING"), (PRIYA, "I lost a shoe"), (THEO, "I found a shoe"),
            (PRIYA, "is it mine?"), (THEO, "it's a left shoe"), (PRIYA, "IT'S MINE"), (MAYA, IMAGE), (MAYA, IMAGE),
            (JORDAN, "best night of the semester no contest"), (MAYA, "FLOOR 4 FOREVER"),
        ])
        run(t + timedelta(minutes=12), [
            (MAYA, "post game food??"), (JORDAN, "omw"), (PRIYA, "jordan we're walking together"),
            (JORDAN, "I know I just like saying it"), (THEO, "I'll save a table at North Commons"),
        ])


def project_rant(day: date) -> None:
    run(at(day, 16, 10), [(MAYA, line) for line in PROJECT_RANT] + [
        (PRIYA, "maya I'm so sorry " + SOB),
        (JORDAN, "\"thank you for coming\" " + SKULL + SKULL),
        (THEO, "honestly that's a good slide"),
    ])


def midterm_day(day: date) -> None:
    run(at(day, 21, 5), [
        (PRIYA, "midterm survivors check in"),
        (MAYA, "I DON'T WANT TO TALK ABOUT IT"),
        (JORDAN, "I wrote my name and then saw god " + SKULL),
        (THEO, "I think it went ok?"),
        (MAYA, "THEO DON'T SAY THAT OUT LOUD"),
    ])


def grades_back(day: date) -> None:
    run(at(day, 13, 40), [
        (MAYA, "I GOT AN A ON THE STATS MIDTERM!!!"),
        (PRIYA, "MAYA!!!"),
        (JORDAN, "my mentor"),
        (MAYA, "I'M FRAMING IT"),
        (THEO, "congrats!!"),
    ])


def thanksgiving(day: date) -> None:
    say(at(day, 13, 51, 7), THEO, THEO_THANKSGIVING)


def last_day(day: date) -> None:
    run(at(day, 18, 0), [
        (MAYA, "LAST DAY OF THE SEMESTER"),
        (PRIYA, "I'm not crying you're crying"),
        (JORDAN, "omw to the dining hall one last time"),
        (THEO, "I said bye to Bingus. he ignored me. it was perfect"),
        (MAYA, "BEST FLOOR. BEST PEOPLE. SEE YOU IN JANUARY"),
        (PRIYA, "I love you guys"),
        (JORDAN, "floor 4 forever " + SKULL),
        (THEO, "see you all next semester"),
    ])


SPECIAL = {
    date(2026, 8, 19): move_in,
    date(2026, 8, 21): first_bingus,
    date(2026, 9, 5): lambda d: football(d, big=False),
    date(2026, 10, 3): lambda d: football(d, big=False),
    date(2026, 10, 14): midterm_day,
    date(2026, 10, 15): midterm_day,
    date(2026, 10, 21): grades_back,
    date(2026, 11, 10): project_rant,
    date(2026, 11, 21): lambda d: football(d, big=True),
    date(2026, 11, 26): thanksgiving,
    date(2026, 12, 12): last_day,
}
BREAK = {date(2026, 11, 25), date(2026, 11, 26), date(2026, 11, 27), date(2026, 11, 28), date(2026, 11, 29)}
WINDOWS = [(8, 10), (11, 13), (14, 16), (17, 19), (20, 22)]  # episode start hours


def build() -> None:
    day = START
    epic_day = date(2026, 10, 8)
    while day <= END:
        if day in SPECIAL:
            SPECIAL[day](day)
            if day in (date(2026, 8, 19), date(2026, 11, 26), date(2026, 12, 12)):
                day += timedelta(days=1)
                continue
        if day in BREAK:
            day += timedelta(days=1)
            continue
        weekend = day.weekday() >= 5
        free = list(range(len(WINDOWS)))
        if day in SPECIAL:
            free = [0, 2]  # special days already filled the rest

        def take(choices):
            options = [w for w in choices if w in free]
            if not options:
                return None
            w = rng.choice(options)
            free.remove(w)
            return w

        if rng.random() < (0.45 if day.weekday() in (0, 2, 3) else 0.25):
            w = take([3])
            if w is not None:
                ep_dinner(at(day, WINDOWS[w][0], rng.randint(0, 50)))
        if rng.random() < 0.12:
            w = take([3, 4])
            if w is not None:
                ep_library(at(day, WINDOWS[w][0], rng.randint(0, 50)))
        if rng.random() < 0.38 and THEO_ALONE:
            w = take([1, 2, 4])
            if w is not None:
                ep_theo_alone(at(day, WINDOWS[w][0], rng.randint(0, 30)))
        for _ in range(rng.randint(2, 4) if weekend else rng.randint(1, 3)):
            w = take(list(free))
            if w is None:
                break
            ep_chatter(at(day, rng.randint(*WINDOWS[w]), rng.randint(0, 40)))
        if rng.random() < 0.22 and PRIYA_3AM and day > START:
            ep_3am(day)
        if day == epic_day:
            say(at(day, 23, 41), PRIYA, PRIYA_EPIC)
        day += timedelta(days=1)


def render() -> str:
    lines = []
    for t, who, text in sorted(events, key=lambda e: e[0]):
        stamp = f"{t.month}/{t.day}/{t.year % 100:02d}, {(t.hour % 12) or 12}:{t.minute:02d}:{t.second:02d}{NNBSP}{'AM' if t.hour < 12 else 'PM'}"
        lines.append(f"[{stamp}] {who}: {text}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    build()
    out = Path(__file__).with_name("demo-chat.txt")
    out.write_text(render(), encoding="utf-8")
    print(f"wrote {out} ({len(events)} lines)")
