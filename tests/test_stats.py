import json
import unittest

from helpers import M, assert_receipts_real, chat
from wrapped.stats import compute, is_hype

ALL = {"Ana", "Ben", "Cy"}


def award(result, key):
    found = [a for a in result["awards"] if a["key"] == key]
    return found[0] if found else None


class TotalsTests(unittest.TestCase):
    def test_group_totals(self):
        msgs = chat(
            ("Ana", "2026-09-01 22:00", "hello there friends"),
            ("Ben", "2026-09-01 22:05", "hi"),
            ("Ana", "2026-09-03 09:00", "", ),
        )
        msgs[2].attachments = 1
        g = compute(msgs, ALL)["group"]
        self.assertEqual(g["messages"], 3)
        self.assertEqual(g["words"], 4)
        self.assertEqual(g["media"], 1)
        self.assertEqual(g["days"], 3)
        self.assertEqual(g["busiest_hour"], "10 PM")
        self.assertEqual(g["busiest_weekday"], "Tuesday")
        self.assertEqual(g["share"], {"Ana": 2, "Ben": 1})

    def test_empty_chat(self):
        self.assertEqual(compute([], ALL)["awards"], [])


class AwardTests(unittest.TestCase):
    def check(self, msgs, key, winner, opted=ALL):
        result = compute(msgs, opted)
        a = award(result, key)
        self.assertIsNotNone(a, key)
        self.assertEqual(a["winner"], winner)
        assert_receipts_real(self, result, msgs)
        return a

    def test_main_character_and_tie(self):
        msgs = chat(
            ("Ben", "2026-09-01 10:00", "one"),
            ("Ana", "2026-09-01 10:01", "a"),
            ("Ana", "2026-09-01 10:02", "b"),
            ("Ben", "2026-09-01 10:03", "two"),
        )
        a = self.check(msgs, "main_character", "Ana")  # 2-2 tie, alphabetical
        self.assertEqual(a["receipt"]["text"], "a")  # start of the 2-message run
        msgs.append(M("Ben", "2026-09-01 10:04", "three"))
        self.check(msgs, "main_character", "Ben")

    def test_novelist(self):
        msgs = chat(
            ("Ana", "2026-09-01 10:00", "short"),
            ("Ana", "2026-09-01 10:01", "short"),
            ("Ana", "2026-09-01 10:02", "this one is a little longer"),
            ("Ben", "2026-09-01 10:03", "four words right here"),
            ("Ben", "2026-09-01 10:04", "four more words here"),
            ("Ben", "2026-09-01 10:05", "and four again ok"),
        )
        a = self.check(msgs, "novelist", "Ben")
        self.assertEqual(a["receipt"]["text"], "four words right here")  # tie -> earliest

    def test_three_am(self):
        msgs = chat(
            ("Ana", "2026-09-01 03:00", "deep thought about the void"),
            ("Ben", "2026-09-01 00:59", "not late enough"),
            ("Ben", "2026-09-01 05:00", "too early"),
            ("Ana", "2026-09-02 01:30", "short"),
        )
        a = self.check(msgs, "three_am", "Ana")
        self.assertEqual(a["receipt"]["ts"], "2026-09-01T03:00:00")
        self.assertIn("2 messages", a["value_text"])

    def test_omw(self):
        msgs = chat(
            ("Cy", "2026-09-01 18:00", "omw"),
            ("Cy", "2026-09-01 18:05", "here"),
            ("Ana", "2026-09-02 18:00", "OMW!!"),
            ("Ben", "2026-09-02 18:10", "where are you"),
            ("Ana", "2026-09-02 18:40", "parking"),
            ("Ana", "2026-09-03 18:00", "on my way now"),
            ("Ana", "2026-09-03 18:01", "lol"),
            ("Ben", "2026-09-03 18:02", "otherwise fine"),  # "otw" inside a word doesn't count
        )
        a = self.check(msgs, "omw", "Ana")
        self.assertIn("2 times", a["value_text"])
        self.assertEqual(a["receipt"]["text"], "OMW!!")  # 40 min until her next message
        self.assertIn("40 min", a["detail"])

    def test_left_on_read(self):
        msgs = chat(
            ("Ben", "2026-09-01 10:00", "anyone at the library?"),
            ("Ben", "2026-09-01 10:30", "hello??"),  # own follow-up doesn't count as an answer
            ("Ana", "2026-09-01 11:45", "no"),
            ("Ana", "2026-09-01 12:00", "lunch?"),
            ("Ben", "2026-09-01 12:59", "yes"),  # answered in 59 minutes
            ("Cy", "2026-09-01 13:00", "is the quiz today?"),
            ("Ana", "2026-09-01 14:00", "yes"),  # exactly 60 minutes: answered
        )
        a = self.check(msgs, "left_on_read", "Ben")
        self.assertIn("2 questions", a["value_text"])
        self.assertEqual(a["receipt"]["text"], "anyone at the library?")  # longest silence

    def test_left_on_read_never_answered(self):
        msgs = chat(("Ana", "2026-09-01 10:00", "who wants pizza?"))
        a = self.check(msgs, "left_on_read", "Ana")
        self.assertEqual(a["detail"], "Nobody ever answered.")

    def test_hype(self):
        self.assertTrue(is_hype("LETS GO"))
        self.assertTrue(is_hype("we won!!!"))
        self.assertFalse(is_hype("OK"))
        self.assertFalse(is_hype("LOL ok"))
        msgs = chat(
            ("Ana", "2026-09-01 10:00", "WE WON THE GAME!!!"),
            ("Ben", "2026-09-01 10:01", "NICE ONE"),
            ("Ben", "2026-09-01 10:02", "yay!!!"),
            ("Ana", "2026-09-01 10:03", "ok"),
        )
        a = self.check(msgs, "hype", "Ben")
        self.assertEqual(a["receipt"]["text"], "NICE ONE")

    def test_speed_demon(self):
        rows = []
        for i in range(6):
            day = f"2026-09-{i + 1:02d}"
            rows += [
                ("Ana", f"{day} 10:00:00", f"question {i}"),
                ("Ben", f"{day} 10:00:0{i + 2}", f"fast {i}"),
                ("Cy", f"{day} 10:20:00", f"slow {i}"),
            ]
        msgs = chat(*rows)
        a = self.check(msgs, "speed_demon", "Ben")
        self.assertEqual(a["receipt"]["text"], "fast 0")
        self.assertEqual(a["context"]["text"], "question 0")
        self.assertIn("2 seconds", a["detail"])

    def test_speed_demon_needs_sample(self):
        msgs = chat(("Ana", "2026-09-01 10:00", "a"), ("Ben", "2026-09-01 10:00:01", "b"))
        self.assertIsNone(award(compute(msgs, ALL), "speed_demon"))

    def test_ghost_and_tie(self):
        msgs = chat(
            ("Ana", "2026-09-01 10:00", "a lot of words"),
            ("Ana", "2026-09-01 10:01", "more"),
            ("Ben", "2026-09-01 10:02", "k"),
            ("Cy", "2026-09-01 10:03", "fine"),
        )
        a = self.check(msgs, "ghost", "Ben")  # Ben and Cy tie on 1
        self.assertEqual(a["receipt"]["text"], "k")
        self.assertIsNone(award(compute(msgs, {"Ana"}), "ghost"))  # needs two candidates

    def test_emoji(self):
        msgs = chat(
            ("Ana", "2026-09-01 10:00", "\U0001F62D\U0001F62D"),
            ("Ben", "2026-09-01 10:01", "\U0001F62D \U0001F480"),
            ("Ben", "2026-09-01 10:02", "\U0001F62D\U0001F62D\U0001F62D"),
        )
        a = self.check(msgs, "emoji", "Ben")
        self.assertEqual(a["emoji"], "\U0001F62D")
        self.assertEqual(a["receipt"]["text"], "\U0001F62D\U0001F62D\U0001F62D")

    def test_group_word(self):
        rows = []
        for i in range(6):
            rows.append(("Ana" if i % 2 else "Ben", f"2026-09-01 10:0{i}", "the bingus is back, very good people"))
        rows.append(("Cy", "2026-09-01 11:00", "lol lol lol lol lol lol"))  # chat slang never wins
        rows += [("Cy", f"2026-09-01 12:0{i}", "zorbly zorbly") for i in range(5)]  # only one user
        msgs = chat(*rows)
        a = self.check(msgs, "group_word", "Ana")  # 3-3 tie with Ben
        self.assertEqual(a["word"], "bingus")
        self.assertIn("6 times", a["value_text"])

    def test_group_word_skips_names(self):
        rows = [("Ana" if i % 2 else "Ben", f"2026-09-01 10:0{i}", "cyrus said hi, ask cyrus") for i in range(6)]
        rows.append(("Cyrus", "2026-09-01 11:00", "hey"))
        a = award(compute(chat(*rows), {"Ana", "Ben", "Cyrus"}), "group_word")
        self.assertNotEqual(a["word"], "cyrus")
        self.assertEqual(a["word"], "said")

    def test_busiest_day(self):
        msgs = chat(
            ("Ana", "2026-09-01 10:00", "quiet day"),
            ("Ben", "2026-09-05 09:00", "morning"),
            ("Cy", "2026-09-05 20:00", "GAME TIME"),
            ("Ana", "2026-09-05 20:01", "yes"),
            ("Ben", "2026-09-05 20:02", "lets go"),
        )
        a = self.check(msgs, "busiest_day", "Cy")
        self.assertEqual(a["date"], "2026-09-05")
        self.assertEqual(a["receipt"]["text"], "GAME TIME")
        self.assertIn("4 messages", a["value_text"])


class OptInTests(unittest.TestCase):
    def build(self):
        rows = []
        for i in range(30):
            rows.append(("Zed Hidden", f"2026-09-{i % 28 + 1:02d} 03:{i:02d}", f"omw!!! WHERE IS EVERYONE?? {'word ' * 40}"))
        for i in range(6):
            rows += [
                ("Ana", f"2026-10-{i + 1:02d} 10:00", "zed is late again, ask Zed? \U0001F62D bingus"),
                ("Ben", f"2026-10-{i + 1:02d} 10:00:01", "omw. @zed say something bingus"),
            ]
        return chat(*rows)

    def test_non_opted_member_never_named_or_quoted(self):
        msgs = self.build()
        result = compute(msgs, {"ana", "Ben"})  # case-insensitive opt-in
        self.assertEqual(result["members"], ["Ana", "Ben"])
        blob = json.dumps(result, ensure_ascii=False).lower()
        self.assertNotIn("zed", blob)
        self.assertNotIn("hidden", blob)
        for a in result["awards"]:
            self.assertIn(a["winner"], {"Ana", "Ben"})
        # the hidden member still counts in group totals, as "someone"
        self.assertEqual(result["group"]["messages"], 42)
        self.assertEqual(result["group"]["share"]["someone"], 30)
        assert_receipts_real(self, result, msgs)

    def test_nobody_opted_in(self):
        result = compute(self.build(), set())
        self.assertEqual(result["awards"], [])
        self.assertEqual(result["group"]["share"], {"someone": 42})


if __name__ == "__main__":
    unittest.main()
