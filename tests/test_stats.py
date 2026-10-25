import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from helpers import M, assert_receipts_real, chat
from wrapped.stats import Redactor, compute, is_hype

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

    def test_main_character_run_is_one_sitting(self):
        msgs = chat(
            ("Ana", "2026-09-01 10:00", "x"),
            ("Ana", "2026-09-01 10:01", "y"),
            ("Ana", "2026-09-01 15:00", "later"),  # 5 hours on: a new run
            ("Ana", "2026-09-01 15:01", "z"),
            ("Ana", "2026-09-01 15:02", "zz"),
            ("Ben", "2026-09-01 15:03", "hi"),
        )
        a = self.check(msgs, "main_character", "Ana")
        self.assertEqual(a["receipt"]["text"], "later")
        self.assertIn("3 in a row", a["detail"])

    def test_durations(self):
        from datetime import timedelta

        from wrapped.stats import fmt_duration

        self.assertEqual(fmt_duration(timedelta(seconds=1)), "1 second")
        self.assertEqual(fmt_duration(timedelta(minutes=40)), "40 min")
        self.assertEqual(fmt_duration(timedelta(hours=1, minutes=42)), "1 h 42 min")
        self.assertEqual(fmt_duration(timedelta(days=3, hours=14)), "3 days 14 h")

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

    def test_tied_main_character_is_not_also_the_ghost(self):
        rows = []
        for i in range(6):
            rows += [("Zed", f"2026-09-01 10:{i:02d}", "same?"), ("Amy", f"2026-09-01 10:{i:02d}:10", "same?")]
        result = compute(chat(*rows), {"Zed", "Amy"})
        self.assertEqual(award(result, "main_character")["winner"], "Amy")
        self.assertIsNone(award(result, "ghost"))  # nobody has fewer messages than the Main Character
        rows.append(("Cy", "2026-09-02 10:00", "k"))
        result = compute(chat(*rows), {"Zed", "Amy", "Cy"})
        self.assertEqual(award(result, "ghost")["winner"], "Cy")

    def test_singular_and_one_person_wording(self):
        msgs = chat(("Solo", "2026-09-01 03:00", "note to self?"), ("Solo", "2026-09-01 12:00", "two"),
                    ("Solo", "2026-09-01 12:01", "three"))
        result = compute(msgs, {"Solo"})
        self.assertEqual(award(result, "three_am")["value_text"], "1 message sent between 1 and 5 AM")
        self.assertEqual(award(result, "novelist")["value_text"], "1.7 words per message on average")
        self.assertEqual(award(result, "novelist")["detail"], "Longest message: 3 words.")
        one = compute(chat(("Ana", "2026-09-01 10:00", "hi")), {"Ana"})
        self.assertEqual(award(one, "main_character")["value_text"], "1 message, 100% of the whole chat")
        two = compute(chat(("Ana", "2026-09-01 10:00", "hi"), ("Ana", "2026-09-01 10:01", "yo"),
                           ("Ben", "2026-09-01 10:02", "k")), {"Ana", "Ben"})
        self.assertEqual(award(two, "ghost")["value_text"], "only 1 message, 33% of the chat")
        self.assertEqual(award(two, "busiest_day")["value_text"], "Tuesday, September 1: 3 messages")

    def test_value_says_among_opted_in_when_someone_hidden_did_more(self):
        rows = [("Zed", f"2026-09-01 03:0{i}", f"WHO IS UP!!! {'word ' * 30}") for i in range(4)]
        rows += [("Ana", "2026-09-01 03:30", "ME!!! long night"), ("Ana", "2026-09-01 10:00", "ok"),
                 ("Ben", "2026-09-01 10:01", "k")]
        result = compute(chat(*rows), {"Ana", "Ben"})
        for key in ("main_character", "three_am", "hype"):
            self.assertTrue(award(result, key)["value_text"].endswith("; the most among people who opted in"), key)
        self.assertNotIn("opted in", award(result, "ghost")["value_text"])  # nobody hidden has fewer
        alone = compute(chat(*rows[4:]), {"Ana", "Ben"})
        self.assertNotIn("opted in", award(alone, "main_character")["value_text"])

    def test_emoji(self):
        msgs = chat(
            ("Ana", "2026-09-01 10:00", "\U0001F62D\U0001F62D"),
            ("Ben", "2026-09-01 10:01", "\U0001F62D \U0001F480"),
            ("Ben", "2026-09-01 10:02", "\U0001F62D\U0001F62D\U0001F62D"),
        )
        a = self.check(msgs, "emoji", "Ben")
        self.assertEqual(a["emoji"], "\U0001F62D")
        self.assertEqual(a["receipt"]["text"], "\U0001F62D\U0001F62D\U0001F62D")

    def test_emoji_counts_whole_flags_families_and_skin_tones(self):
        from wrapped import profiles
        from wrapped.stats import EMOJI
        family, thumb, thumb_tone, flag = "\U0001F468‍\U0001F469‍\U0001F467", "\U0001F44D", "\U0001F44D\U0001F3FD", "\U0001F1FA\U0001F1F8"
        heart = "❤️"
        self.assertEqual(EMOJI.findall(f"{flag}{flag} {family} {thumb_tone}{thumb} {heart}"),
                         [flag, flag, family, thumb_tone, thumb, heart])
        rows = []
        for i in range(10):
            rows.append(("Ari", f"2026-09-01 10:{i:02d}", flag + flag))
            rows.append(("Bo", f"2026-09-01 10:{i:02d}:05", f"{family} {thumb_tone}"))
        rows.append(("Bo", "2026-09-01 11:00", thumb))
        msgs = chat(*rows)
        result = compute(msgs, {"Ari", "Bo"})
        a = award(result, "emoji")
        self.assertEqual(a["emoji"], flag)
        self.assertEqual(a["value_text"], f"{flag} used 20 times, every single one by Ari")
        bo = next(p for p in profiles.build(msgs, result) if p["name"] == "Bo")
        self.assertEqual({e["emoji"]: e["count"] for e in bo["top_emoji"]}, {family: 10, thumb_tone: 10, thumb: 1})

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

    def test_case_variant_never_inherits_consent(self):
        # "Maya" opted in; "maya" is someone else who didn't. Set iteration
        # order depends on the hash seed, so check under several seeds.
        code = (
            "import json\n"
            "from helpers import chat\n"
            "from wrapped.stats import compute\n"
            "msgs = chat(('maya', '2026-09-01 12:05', 'secret one?'), ('maya', '2026-09-01 12:06', 'secret two?'),\n"
            "            ('Maya', '2026-09-01 12:07', 'public'), ('Leo', '2026-09-01 12:08', 'ok'))\n"
            "r = compute(msgs, {'Maya', 'Leo'})\n"
            "amb = compute(msgs, {'MAYA'})\n"
            "print(json.dumps([r['members'], amb['members'], json.dumps(r).count('secret')]))\n"
        )
        here = Path(__file__).resolve().parent
        for seed in range(8):
            env = dict(os.environ, PYTHONHASHSEED=str(seed), PYTHONDONTWRITEBYTECODE="1",
                       PYTHONPATH=os.pathsep.join([str(here), str(here.parent)]))
            proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=60)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            members, ambiguous, secrets = json.loads(proc.stdout)
            self.assertEqual(members, ["Leo", "Maya"], f"seed {seed}")
            self.assertEqual(ambiguous, [], f"seed {seed}: a case-only match with two authors names nobody")
            self.assertEqual(secrets, 0, f"seed {seed}")

    def test_nickname_never_reaches_receipts_or_top_words(self):
        from wrapped import profiles
        rows = []
        for i in range(6):
            rows.append(("Kayla Brooks", f"2026-09-01 10:{i:02d}", "who is coming??"))
            rows.append(("Ana", f"2026-09-01 10:{i:02d}:30", "lol ok Kayla, Kay is so zorbly. @Kayla where r u"))
            rows.append(("Ana", f"2026-09-01 10:{i:02d}:40", "kay kay KAY zorbly zorbly zorbly zorbly zorbly zorbly zorbly zorbly zorbly!!!"))
        msgs = chat(*rows)
        result = compute(msgs, {"Ana"})
        self.assertTrue(result["awards"])
        for a in result["awards"]:
            self.assertEqual(a["receipt"]["text"], "lol ok someone, someone is so zorbly. someone where r u")
        assert_receipts_real(self, result, msgs)
        [ana] = profiles.build(msgs, result)
        top = {w["word"] for w in ana["top_words"]}
        self.assertIn("zorbly", top)
        self.assertFalse(top & {"kay", "kayla", "brooks"}, top)

    def test_nobody_opted_in(self):
        result = compute(self.build(), set())
        self.assertEqual(result["awards"], [])
        self.assertEqual(result["group"]["share"], {"someone": 42})


class NameVariantTests(unittest.TestCase):
    def test_top_words_and_group_word_skip_name_variants(self):
        from wrapped import profiles
        rows = []
        for i in range(20):
            rows += [("Ana", f"2026-09-01 10:{i:02d}", "zork with kayla and kaylas kaylaaa crew tonight?"),
                     ("Ben", f"2026-09-01 10:{i:02d}:20", "kayla kaylas zork kaylaaa yes"),
                     ("Kayla Brooks", f"2026-09-01 10:{i:02d}:40", "hi")]
        rows += [("Ana", "2026-09-02 10:00", "zork tonight"), ("Ben", "2026-09-02 10:01", "zork zork")]
        msgs = chat(*rows)
        result = compute(msgs, {"Ana", "Ben"})
        people = profiles.build(msgs, result)
        blob = json.dumps([result, people]).lower()
        self.assertNotIn("kayla", blob)
        self.assertEqual(award(result, "group_word")["word"], "zork")
        self.assertIn("zork", {w["word"] for w in people[0]["top_words"]})


class RedactorTests(unittest.TestCase):
    def test_names_nicknames_and_handles(self):
        r = Redactor({"Kayla Brooks"})
        self.assertEqual(r("Kayla Brooks, kayla, KAYLA, Kay and Kayl, brooks"),
                         "someone, someone, someone, someone and someone, someone")
        self.assertEqual(r("okay kay"), "okay kay")  # nicknames are replaced only when capitalised...
        self.assertFalse(r.quotable("okay kay"))  # ...and any other casing makes the message unquotable
        self.assertFalse(r.quotable("kay where are you?? KAY come on!!!"))
        self.assertTrue(r.quotable("Kay where are you?? KAYLA!!!"))

    def test_name_that_is_an_ordinary_word_only_when_capitalised(self):
        r = Redactor({"Will"})
        self.assertEqual(r("I will be there, will you? I WILL"), "I will be there, will you? I WILL")
        self.assertEqual(r("Will is late, ask @Will"), "someone is late, ask someone")
        self.assertTrue(r.quotable("ask Will about it"))
        for text in ("I will be there", "I WILL", "will!!!", "Will you come?", "ok. Will you come?", "yes!\nWill do"):
            self.assertFalse(r.quotable(text), text)  # not mangled, and not quoted either

    def test_lowercase_ordinary_word_name_is_never_quoted(self):
        rows = []
        for i in range(6):
            rows += [("Mark", f"2026-09-01 10:{i:02d}", "hey?"),
                     ("Ana", f"2026-09-01 10:{i:02d}:10", "mark said he would come?? mark pls"),
                     ("Ana", f"2026-09-01 10:{i:02d}:20", "see you Mark"),
                     ("Ben", f"2026-09-01 10:{i:02d}:30", "GRACE YOUNG!!! grace young")]
        msgs = chat(*rows) + chat(*[("Grace Young", f"2026-09-02 10:0{i}", "hi") for i in range(3)])
        result = compute(msgs, {"Ana", "Ben"})
        blob = json.dumps(result).lower()
        self.assertNotIn("mark", blob)
        self.assertNotIn("grace", blob)
        self.assertIn("see you someone", blob)
        assert_receipts_real(self, result, msgs)

    def test_accents_fold_both_ways(self):
        r = Redactor({"Zoë Müller"})
        self.assertEqual(r("zoe where?? Zoe!!! muller? Mueller ZOË"), "someone where?? someone!!! someone? someone someone")
        self.assertEqual(Redactor({"Zoe Mueller"})("Zoë Müller, MÜLLER"), "someone someone, someone")
        self.assertEqual(Redactor({"Strauß"})("strauss and Strauß"), "someone and someone")

    def test_stretched_names_match_their_name(self):
        r = Redactor({"Ana Lopez"})
        self.assertEqual(r("anaaa where r u?? ANAAA Annnaa"), "someone where r u?? someone someone")
        for text in ("analysis of Anna", "banana"):  # a 3-letter name isn't a prefix rule, and nn isn't n
            self.assertTrue(r.quotable(text), text)
            self.assertEqual(r(text), text)
        self.assertEqual(Redactor({"Sam"})("saaam!!!"), "someone!!!")

    def test_accented_and_stretched_names_stay_out_of_top_words(self):
        from wrapped import profiles
        rows = []
        for i in range(6):
            rows += [("Zoë Müller", f"2026-09-01 10:{i:02d}", "hey"), ("Ana Lopez", f"2026-09-01 10:{i:02d}:05", "yo"),
                     ("Bea", f"2026-09-01 10:{i:02d}:10", "zoe muller mueller anaaa zork analysis")]
        msgs = chat(*rows)
        [bea] = profiles.build(msgs, compute(msgs, {"Bea"}))
        top = {w["word"] for w in bea["top_words"]}
        self.assertFalse(top & {"zoe", "muller", "mueller", "anaaa"}, top)
        self.assertIn("analysis", top)

    def test_name_shared_with_an_opted_in_member_is_never_quoted(self):
        r = Redactor({"maya"}, named={"Maya"})
        self.assertFalse(r.quotable("hi Maya"))
        self.assertTrue(r.quotable("hi Leo"))

    def test_nicknames_skip_ordinary_words_and_contractions(self):
        self.assertEqual(Redactor({"Theodore"})("The party, Theo?"), "The party, someone?")
        self.assertEqual(Redactor({"Donald"})("Don't do it, Don"), "Don't do it, someone")

    def test_names_glued_to_punctuation_or_emoji(self):
        for hidden in ("kayla.brooks", "Kayla\U0001F338", "~ Kayla", "kayla_b"):
            r = Redactor({hidden})
            self.assertEqual(r("Kayla where are you?? kayla!!!"), "someone where are you?? someone!!!", hidden)
        r = Redactor({"kayla_b"})
        self.assertEqual(r("@kayla_b and Kayla\U0001F338"), "someone and someone\U0001F338")
        self.assertEqual(Redactor({"kayla.brooks"})("BROOKS?"), "someone?")

    def test_variants_of_a_name_are_never_quoted(self):
        r = Redactor({"Kayla Brooks"})
        self.assertFalse(r.quotable("kaylas crew"))
        self.assertFalse(r.quotable("Kaylaaas crew"))
        self.assertEqual(r("Kaylaaa!!!"), "someone!!!")  # stretched, it is still her name
        self.assertTrue(r.quotable("Kaylaaa!!!"))
        self.assertTrue(r.quotable("Kayla's party, Brooks's dog"))
        self.assertEqual(r("Kayla's party, Brooks's dog"), "someone's party, someone's dog")

    def test_nickname_of_a_hidden_name_spares_an_opted_in_name(self):
        r = Redactor({"Benjamin"}, named={"Ben"})
        self.assertEqual(r("Ben and Benjamin and Benj"), "Ben and someone and someone")

    def test_phone_numbers_make_a_message_unquotable(self):
        # A message with a phone number isn't rewritten; it just can't be a receipt.
        r = Redactor({"+1 (555) 123-4567"})
        for text in ("@15551234567 call me back 555 times!!!", "text +1 (555) 123-4567 later",
                     "my number is 555-123-4567 call me?", "or (555) 123-4567", "call +44 7911 123456?",
                     "my number is 4805551234", "order #1234567890 shipped?", "pay me 1000000000 dollars?",
                     # India, UK, Australia, France
                     "98765 43210", "call 098765 43210", "98765-43210", "+91 98765 43210", "07911 123456",
                     "020 7946 0958", "(02) 9374 4000", "0412 345 678", "01 23 45 67 89", "555.123.4567?",
                     "+1 555 123 4567?", "call 2 98765 43210"):
            self.assertFalse(r.quotable(text), text)

    def test_ordinary_numbers_stay_quotable_and_untouched(self):
        r = Redactor({"Kayla"})
        for text in ("lunch @12 tomorrow?", "meet @7pm!!!", "countdown 10 9 8 7 6 5 4 3 2 1!!!",
                     "scores 100 100 100 100 lol?", "train at 2026-10-24 10:30?", "temps 1.5 2.5 3.5 4.5 5.5?",
                     "it's 12:30 on 10/24?", "tracking 1Z999AA10123456784?", "code is 4821, room 1102, bldg 7?",
                     "scores 100 200 300 400", "zip 85281-1234?", "isbn 978-0-306-40615-7?", "pi 3.14159 2.71828",
                     "12 34 56 78 90 go", "$1,000,000,000 lol"):
            self.assertTrue(r.quotable(text), text)
            self.assertEqual(r(text), text)

    def test_unquotable_message_gives_way_to_the_next_best_receipt(self):
        msgs = chat(("Ana", "2026-09-01 10:00", "my number is 555-123-4567 call me any time this week ok?"),
                    ("Ana", "2026-09-01 10:01", "see you there"), ("Ana", "2026-09-01 10:02", "ok"),
                    ("Ben", "2026-09-01 10:03", "k"))
        result = compute(msgs, {"Ana", "Ben"})
        self.assertEqual(award(result, "novelist")["receipt"]["text"], "see you there")
        self.assertEqual(award(result, "novelist")["detail"], "One of their longest: 3 words.")
        self.assertNotIn("555", json.dumps(result))
        assert_receipts_real(self, result, msgs)

    def test_phone_author_mention_never_quoted(self):
        rows = []
        for i in range(8):
            rows.append(("+1 (555) 123-4567", f"2026-09-01 10:{i:02d}", "hey all?"))
            rows.append(("Ana", f"2026-09-01 10:{i:02d}:15", "@15551234567 call me back 555 times!!!"))
        msgs = chat(*rows)
        blob = json.dumps(compute(msgs, {"Ana"}), ensure_ascii=False)
        self.assertNotIn("15551234567", blob)
        self.assertNotIn("123-4567", blob)


if __name__ == "__main__":
    unittest.main()
