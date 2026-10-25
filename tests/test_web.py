"""The web app's payloads, profiles, captions (mocked Claude, no network) and the FastAPI server."""

import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from contextlib import redirect_stdout
from unittest import mock

from wrapped import captions, importers, profiles, webapi
from wrapped.stats import compute

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "demo" / "demo-chat.txt"
HIDDEN = ("jordan", "theo")

try:
    from fastapi.testclient import TestClient

    from wrapped import server
except ImportError:  # the web extra isn't installed (plain python3)
    server = None


def demo_messages():
    return importers.parse_whatsapp(DEMO.read_text(encoding="utf-8-sig"))


def partial_payload(client=None):
    return webapi.wrapped_payload(demo_messages(), ["Maya", "Priya"], "Floor 4", client)


def assert_hidden_absent(test, text):
    low = text.lower()
    for name in HIDDEN:
        test.assertNotRegex(low, rf"\b{name}\b", name)


def response(body: str, stop_reason="end_turn"):
    return SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=body)])


def fake_client(resp=None, error=None):
    create = mock.Mock(side_effect=error) if error else mock.Mock(return_value=resp)
    return SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create))), create


class FormatTests(unittest.TestCase):
    def test_detect(self):
        self.assertEqual(webapi.detect_format("[8/19/26, 2:03:11 PM] Maya: hi"), "whatsapp")
        self.assertEqual(webapi.detect_format('{"guild": {}, "messages": []}'), "discord")
        self.assertEqual(webapi.detect_format('{"participants": [], "messages": [{"sender_name": "a"}]}'), "instagram")
        self.assertEqual(webapi.detect_format("timestamp,author,text\n2026-09-01T10:00,A,hi"), "csv")

    def test_fixtures_detect_as_their_format(self):
        ig = next((ROOT / "tests" / "fixtures" / "instagram").rglob("message_1.json"))
        _, fmt = webapi.parse_upload(ig.read_bytes())
        self.assertEqual(fmt, "instagram")
        _, fmt = webapi.parse_upload(DEMO.read_bytes())
        self.assertEqual(fmt, "whatsapp")

    def test_errors_are_plain_and_never_quote_the_upload(self):
        with self.assertRaises(webapi.UploadError):
            webapi.parse_upload(b"x" * (webapi.MAX_BYTES + 1))
        with self.assertRaises(webapi.UploadError):
            webapi.parse_upload(b"\xff\xfe\x00secret")
        with self.assertRaises(webapi.UploadError) as e:
            webapi.parse_upload(b'{"messages": [{"timestamp": "nope secret-text"}]}', "discord")
        self.assertNotIn("secret", str(e.exception))
        with self.assertRaises(webapi.UploadError):
            webapi.parse_upload(b"just words, no chat secret", "whatsapp")


class PayloadTests(unittest.TestCase):
    def test_members_lists_everyone_with_counts(self):
        p = webapi.members_payload(demo_messages(), "whatsapp")
        self.assertEqual({m["name"] for m in p["members"]}, {"Maya", "Jordan", "Priya", "Theo"})
        self.assertEqual(sum(m["messages"] for m in p["members"]), p["messages"])

    def test_demo_has_profiles_group_and_captions(self):
        p = webapi.demo_payload()
        self.assertEqual(len(p["result"]["awards"]), 11)
        self.assertEqual([x["name"] for x in p["profiles"]], ["Jordan", "Maya", "Priya", "Theo"])
        self.assertEqual(p["captions"]["source"], "template")
        self.assertEqual(set(p["captions"]["awards"]), {a["key"] for a in p["result"]["awards"]})
        self.assertEqual(p["group"]["others"], 0)
        self.assertEqual(p["group"]["group_word"]["key"], "group_word")

    def test_non_opted_names_absent_from_the_whole_payload(self):
        p = partial_payload()
        self.assertEqual([x["name"] for x in p["profiles"]], ["Maya", "Priya"])
        self.assertEqual(p["group"]["others"], 2)
        assert_hidden_absent(self, json.dumps(p, ensure_ascii=False))


class ProfileTests(unittest.TestCase):
    def setUp(self):
        msgs = demo_messages()
        self.result = compute(msgs, {"Maya", "Priya", "Jordan", "Theo"})
        self.people = {p["name"]: p for p in profiles.build(msgs, self.result)}

    def test_fields(self):
        maya = self.people["Maya"]
        self.assertEqual(maya["handle"], "@maya")
        self.assertEqual(maya["initials"], "M")
        self.assertTrue(0 <= maya["hue"] < 360)
        self.assertEqual(maya["hue"], profiles.hue("Maya"))
        self.assertGreater(maya["messages"], 0)
        self.assertEqual(maya["posts"], len(maya["receipts"]))
        self.assertTrue(maya["peak_hour"].endswith(("AM", "PM")))

    def test_awards_and_posts_match_the_result(self):
        for a in self.result["awards"]:
            winner = self.people[a["winner"]]
            self.assertIn(a["key"], [x["key"] for x in winner["awards"]])
            texts = [r["text"] for r in self.people[a["receipt"]["author"]]["receipts"]]
            self.assertIn(a["receipt"]["text"], texts)

    def test_top_words_skip_names(self):
        names = {"maya", "priya", "jordan", "theo"}
        for p in self.people.values():
            self.assertFalse(names & {w["word"] for w in p["top_words"]}, p["name"])

    def test_reactions_come_from_the_data(self):
        from helpers import chat

        msgs = chat(*[("Ana", f"2026-09-0{i + 1} 10:00", f"word{i} ok") for i in range(5)])
        msgs[0].reactions = {"😂": 3}
        result = compute(msgs, {"Ana"})
        people = profiles.build(msgs, result)
        posts = people[0]["receipts"]
        self.assertTrue(posts)
        for post in posts:
            if post["ts"] == msgs[0].ts.isoformat():
                self.assertEqual(post["reactions"], {"😂": 3})

    def test_handles(self):
        self.assertEqual(profiles.handle("Renée Li"), "@renée_li")
        self.assertEqual(profiles.initials("renée li"), "RL")


class CaptionTests(unittest.TestCase):
    def setUp(self):
        msgs = demo_messages()
        self.result = compute(msgs, {"Maya", "Priya"})
        self.people = profiles.build(msgs, self.result)
        self.awards = self.result["awards"]

    def test_templates_by_default(self):
        caps = captions.captions(self.awards, self.people)
        self.assertEqual(caps["source"], "template")
        for a in self.awards:
            self.assertIn(a["winner"], caps["awards"][a["key"]])
        for p in self.people:
            self.assertIn(f"{p['messages']:,}", caps["bios"][p["name"]])

    def test_template_bio_singular(self):
        bio = captions.template_bio({"messages": 1, "peak_hour": "3 PM", "awards": []})
        self.assertTrue(bio.startswith("1 message, mostly around 3 PM."), bio)

    def test_request_shape_and_nothing_hidden_is_sent(self):
        body = json.dumps({"captions": [], "bios": []})
        client, create = fake_client(response(body))
        captions.captions(self.awards, self.people, client)
        kwargs = create.call_args.kwargs
        self.assertEqual(kwargs["model"], "claude-opus-5-5")
        self.assertEqual(kwargs["betas"], ["server-side-fallback-2026-07-01"])
        self.assertEqual(kwargs["fallbacks"], "default")
        self.assertEqual(kwargs["output_config"]["effort"], "low")
        self.assertEqual(kwargs["output_config"]["format"]["type"], "json_schema")
        self.assertNotIn("temperature", kwargs)
        sent = json.dumps(kwargs, ensure_ascii=False)
        assert_hidden_absent(self, sent)
        self.assertEqual(kwargs["messages"][0]["content"], captions.request_payload(self.awards, self.people))
        facts = json.loads(kwargs["messages"][0]["content"])
        self.assertEqual(set(facts["awards"][0]), {"key", "title", "winner", "value_text", "receipt"})

    def test_uses_grounded_lines_and_rejects_invented_numbers(self):
        a0, a1 = self.awards[0], self.awards[1]
        n0 = next(iter(__import__("re").findall(r"\d+", a0["value_text"])))
        body = json.dumps({
            "captions": [
                {"key": a0["key"], "caption": f"{a0['winner']} sent {n0} messages. Legend."},
                {"key": a1["key"], "caption": f"{a1['winner']} wrote 98765 words at once."},
                {"key": "not_an_award", "caption": "ignored"},
            ],
            "bios": [{"name": self.people[0]["name"], "bio": "Professional yapper."}, {"name": "Jordan", "bio": "x"}],
        })
        client, _ = fake_client(response(body))
        caps = captions.captions(self.awards, self.people, client)
        self.assertEqual(caps["source"], "claude")
        self.assertEqual(caps["awards"][a0["key"]], f"{a0['winner']} sent {n0} messages. Legend.")
        self.assertEqual(caps["awards"][a1["key"]], captions.template_caption(a1))
        self.assertNotIn("not_an_award", caps["awards"])
        self.assertEqual(caps["bios"][self.people[0]["name"]], "Professional yapper.")
        self.assertNotIn("Jordan", caps["bios"])

    def test_failures_fall_back_to_templates(self):
        expected = captions.templates(self.awards, self.people)
        for client, _ in (
            fake_client(error=RuntimeError("network")),
            fake_client(response("{}", stop_reason="refusal")),
            fake_client(response('{"captions": [', stop_reason="max_tokens")),
            fake_client(response("not json")),
        ):
            self.assertEqual(captions.captions(self.awards, self.people, client), expected)

    def test_make_client_keeps_the_key_out_of_env_and_output(self):
        done = subprocess.CompletedProcess([], 0, stdout="sk-test-key\n", stderr="")
        fake_sdk = mock.Mock()
        with mock.patch.object(subprocess, "run", return_value=done), mock.patch.object(captions, "anthropic", fake_sdk), \
                mock.patch.dict(os.environ, {}, clear=True):
            captions.make_client()
            self.assertNotIn("ANTHROPIC_API_KEY", os.environ)
        fake_sdk.Anthropic.assert_called_once_with(api_key="sk-test-key")

    def test_make_client_none_without_key_or_sdk(self):
        missing = subprocess.CompletedProcess([], 44, stdout="", stderr="")
        with mock.patch.object(subprocess, "run", return_value=missing), mock.patch.object(captions, "anthropic", mock.Mock()):
            self.assertIsNone(captions.make_client())
        with mock.patch.object(captions, "anthropic", None):
            self.assertIsNone(captions.make_client())


class StaticDemoTests(unittest.TestCase):
    def test_dump_demo_matches_the_api_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "demo.json"
            with redirect_stdout(io.StringIO()):
                self.assertEqual(webapi.main(["--dump-demo", str(out)]), 0)
            self.assertEqual(json.loads(out.read_text(encoding="utf-8")), json.loads(json.dumps(webapi.demo_payload())))

    def test_built_demo_json_is_current(self):
        baked = ROOT / "web" / "dist" / "demo.json"
        if not baked.exists():
            self.skipTest("web/dist/demo.json not built (npm run build:static)")
        self.assertEqual(json.loads(baked.read_text(encoding="utf-8")), json.loads(json.dumps(webapi.demo_payload())))


@unittest.skipIf(server is None, "fastapi not installed (pip install -e '.[web]')")
class ServerTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(server.create_app(dist=Path("/nonexistent")))

    def post(self, path, data: bytes, **fields):
        return self.client.post(path, files={"file": ("chat.txt", data, "text/plain")}, data=fields)

    def test_health_and_demo(self):
        self.assertEqual(self.client.get("/api/health").json()["captions"], "template")
        got = self.client.get("/api/demo").json()
        self.assertEqual(got, json.loads(json.dumps(webapi.demo_payload())))

    def test_members_then_wrapped_with_two_opted_out(self):
        data = DEMO.read_bytes()
        members = self.post("/api/members", data, format="auto").json()
        self.assertEqual(members["format"], "whatsapp")
        self.assertEqual(len(members["members"]), 4)
        r = self.client.post(
            "/api/wrapped",
            files={"file": ("chat.txt", data, "text/plain")},
            data={"format": "whatsapp", "optin": ["Maya", "Priya"], "name": "Floor 4"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual([p["name"] for p in r.json()["profiles"]], ["Maya", "Priya"])
        assert_hidden_absent(self, r.text)

    def test_large_upload_never_touches_disk(self):
        data = DEMO.read_bytes()
        big = data * (2 * 1024 * 1024 // len(data) + 1)  # > 1 MB, where Starlette would spill to a temp file
        with mock.patch("tempfile.SpooledTemporaryFile.rollover", side_effect=AssertionError("spilled to disk")):
            r = self.post("/api/members", big)
        self.assertEqual(r.status_code, 200, r.text)

    def test_size_cap(self):
        with mock.patch.object(server, "BODY_CAP", 1000):
            r = self.post("/api/members", b"x" * 5000)
        self.assertEqual(r.status_code, 413)
        self.assertIn("MB", r.json()["error"])

    def test_bad_uploads_get_plain_errors(self):
        r = self.post("/api/members", b"\xff\xfe secret stuff")
        self.assertEqual(r.status_code, 400)
        self.assertNotIn("secret", r.text)
        r = self.client.post("/api/members", data={"format": "auto"})
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/api/members", content=b"secret raw", headers={"content-type": "text/plain"})
        self.assertEqual(r.status_code, 400)
        self.assertNotIn("secret", r.text)


if __name__ == "__main__":
    unittest.main()
