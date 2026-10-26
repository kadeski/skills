import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SERVER = Path(__file__).resolve().parents[2] / "plugins" / "study" / "server"
sys.path.insert(0, str(SERVER))

import store  # noqa: E402


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "data"
        self.s = store.Store(self.root)

    def tearDown(self):
        self.tmp.cleanup()


class DataDirTest(unittest.TestCase):
    def test_order_and_placeholders(self):
        env = dict(os.environ)
        try:
            os.environ["CLAUDE_PLUGIN_OPTION_DATA_DIR"] = "~/from-env"
            self.assertEqual(store.resolve_data_dir("/x/arg"), Path("/x/arg"))
            self.assertEqual(store.resolve_data_dir(""), Path(os.path.expanduser("~/from-env")))
            self.assertEqual(
                store.resolve_data_dir("${user_config.data_dir}"), Path(os.path.expanduser("~/from-env"))
            )
            del os.environ["CLAUDE_PLUGIN_OPTION_DATA_DIR"]
            self.assertEqual(store.resolve_data_dir(None), Path(os.path.expanduser("~/Study")))
        finally:
            os.environ.clear()
            os.environ.update(env)


class FilesTest(StoreTest):
    def test_write_json_is_atomic_and_creates_format(self):
        self.s.write_json("goals/a-1234/goal.json", {"id": "a-1234"})
        self.assertEqual(self.s.read_json("format.json"), {"format": 1})
        self.assertEqual(self.s.read_json("goals/a-1234/goal.json"), {"id": "a-1234"})
        self.s.write_json("goals/a-1234/goal.json", {"id": "a-1234", "v": 2})
        leftovers = [p.name for p in (self.root / "goals" / "a-1234").iterdir() if p.name != "goal.json"]
        self.assertEqual(leftovers, [])

    def test_failed_write_keeps_old_file(self):
        self.s.write_json("x.json", {"ok": True})
        with self.assertRaises(TypeError):
            self.s.write_json("x.json", {"bad": object()})
        self.assertEqual(self.s.read_json("x.json"), {"ok": True})
        self.assertEqual([p.name for p in self.root.iterdir() if p.name.startswith(".")], [])

    def test_newer_format_refuses_writes(self):
        self.root.mkdir(parents=True)
        (self.root / "format.json").write_text('{"format": 2}')
        with self.assertRaises(store.FormatError):
            self.s.write_json("x.json", {})
        with self.assertRaises(store.FormatError):
            self.s.append_jsonl("graph/propositions.jsonl", {"op": "add"})
        self.assertFalse((self.root / "x.json").exists())

    def test_read_missing(self):
        self.assertIsNone(self.s.read_json("nope.json"))
        self.assertEqual(self.s.read_jsonl("nope.jsonl"), [])

    def test_append_entry_numbers_and_survives_torn_line(self):
        rel = "goals/g-0000/sessions/2026-10-25-abcd.jsonl"
        self.s.append_entry(rel, {"type": "start"})
        with open(self.root / rel, "ab") as f:
            f.write(b'{"n": 2, "type": "torn"')
        e = self.s.append_entry(rel, {"type": "learner", "text": "hi"})
        self.assertEqual(e["n"], 2)
        self.assertEqual([x["n"] for x in self.s.read_jsonl(rel)], [1, 2])
        self.assertRegex(e["at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_appends_from_many_processes(self):
        rel = "goals/g-0000/sessions/2026-10-25-abcd.jsonl"
        self.s.check_writable()
        code = (
            "import sys; sys.path.insert(0, sys.argv[1]); import store\n"
            "s = store.Store(sys.argv[2])\n"
            "for i in range(40): s.append_entry(sys.argv[3], {'type': 'learner', 'text': 'x' * 2000})\n"
        )
        procs = [
            subprocess.Popen([sys.executable, "-I", "-c", code, str(SERVER), str(self.root), rel])
            for _ in range(4)
        ]
        for p in procs:
            self.assertEqual(p.wait(timeout=60), 0)
        entries = self.s.read_jsonl(rel)
        self.assertEqual(sorted(e["n"] for e in entries), list(range(1, 161)))
        with open(self.root / rel, "rb") as f:
            self.assertEqual(len(f.read().splitlines()), 160)

    def test_bad_ids_refused(self):
        for bad in ("../x", "a/b", "", ".hidden", "abc\n", None):
            with self.assertRaises(store.StoreError):
                self.s.goal_rel(bad)


class GoalsAndLogsTest(StoreTest):
    def test_goal_round_trip_and_order(self):
        a = self.s.new_goal_id("Two-step équations!")
        self.assertRegex(a, r"^two-step-equations-[a-z0-9]{4}$")
        self.s.write_goal({"id": a, "title": "A"})
        time.sleep(1.1)
        b = self.s.new_goal_id("B")
        self.s.write_goal({"id": b, "title": "B"})
        self.assertEqual([g["id"] for g in self.s.list_goals()], [b, a])

    def test_logs_ordered_by_first_entry(self):
        self.s.write_goal({"id": "g-0000"})
        self.s.write_json("goals/g-0000/sessions/2026-10-25-zzzz.jsonl.tmp", {})
        for log_id, at in (("2026-10-25-zzzz", "2026-10-25T01:00:00Z"), ("2026-10-25-aaaa", "2026-10-25T02:00:00Z")):
            self.s.append_jsonl(self.s.log_rel("g-0000", log_id), {"n": 1, "at": at, "type": "start"})
        self.assertEqual(self.s.log_ids("g-0000"), ["2026-10-25-zzzz", "2026-10-25-aaaa"])
        entries = self.s.goal_entries("g-0000")
        self.assertEqual([e["log"] for e in entries], ["2026-10-25-zzzz", "2026-10-25-aaaa"])
        self.assertEqual(self.s.log_rel(None, "2026-10-25-aaaa"), "practice/sessions/2026-10-25-aaaa.jsonl")


class MarkerTest(StoreTest):
    def test_live_stale_and_deleted(self):
        sid = "0b8c9d6e-1111-2222-3333-444455556666"
        self.assertIsNone(self.s.read_marker(sid))
        marker = {"mode": "study", "goal": "g-0000", "log": "2026-10-25-abcd", "started": store.now()}
        self.s.write_marker(sid, marker)
        self.assertEqual(self.s.read_marker(sid), marker)
        later = time.time() + store.MARKER_TTL + 60
        self.assertIsNone(self.s.read_marker(sid, at=later))
        self.s.delete_marker(sid)
        self.assertIsNone(self.s.read_marker(sid))
        self.s.delete_marker(sid)

    def test_recent_log_entry_keeps_old_marker_live(self):
        sid = "abc"
        self.s.write_marker(sid, {"mode": "study", "goal": "g-0000", "log": "l-1", "started": "2026-01-01T00:00:00Z"})
        old = time.time() - 3 * store.MARKER_TTL
        os.utime(self.root / self.s.marker_rel(sid), (old, old))
        self.assertIsNone(self.s.read_marker(sid))
        self.s.append_log("g-0000", "l-1", {"type": "learner", "text": "hi"})
        self.assertIsNotNone(self.s.read_marker(sid))


class GraphTest(StoreTest):
    def test_fold(self):
        for op in (
            {"op": "add", "id": "p_a", "statement": "A", "sources": [{"goal": "g"}]},
            {"op": "add", "id": "p_b", "statement": "B"},
            {"op": "add", "id": "p_c", "statement": "C"},
            {"op": "source", "id": "p_a", "source": {"source": "src_1"}},
            {"op": "alias", "id": "p_a", "text": "a"},
            {"op": "alias", "id": "p_zz", "text": "ignored"},
            {"op": "delete", "id": "p_c"},
        ):
            self.s.append_jsonl("graph/propositions.jsonl", op)
        self.s.append_jsonl("graph/chains.jsonl", {"op": "add", "id": "c_1", "premises": ["p_a"], "conclusion": "p_b"})
        self.s.append_jsonl("graph/chains.jsonl", {"op": "add", "id": "c_2", "premises": ["p_c"], "conclusion": "p_b"})
        props, chains = self.s.graph()
        self.assertEqual(list(props), ["p_a", "p_b"])
        self.assertEqual(props["p_a"]["sources"], [{"goal": "g"}, {"source": "src_1"}])
        self.assertEqual(props["p_a"]["aliases"], ["a"])
        self.assertEqual(list(chains), ["c_1"])
        self.assertNotIn("aliases", chains["c_1"])


class LogReadingTest(unittest.TestCase):
    def q(self, qid, step=None, key=("A",)):
        return {"type": "question", "id": qid, "step": step, "key": list(key)}

    def test_open_question_and_ungraded(self):
        entries = [self.q("q1"), {"type": "answer", "question": "q1"}, self.q("q2")]
        self.assertEqual(store.open_question(entries)["id"], "q2")
        self.assertEqual([e["id"] for e in store.ungraded(entries)], ["q1"])
        entries.append({"type": "verdict", "question": "q2", "verdict": "skipped"})
        entries.append({"type": "verdict", "question": "q1", "verdict": "right"})
        self.assertIsNone(store.open_question(entries))
        self.assertEqual(store.ungraded(entries), [])

    def test_step_statuses(self):
        plan = {"steps": [{"id": "s1"}, {"id": "s2"}, {"id": "s3"}, {"id": "s4"}]}
        self.assertEqual(set(store.step_statuses(plan, []).values()), {"upcoming"})
        got = store.step_statuses(plan, [self.q("q1"), self.q("q2", "s2"), self.q("q3", "s4"), self.q("q4", "s1"), self.q("q5", "s9")])
        self.assertEqual(got, {"s1": "current", "s2": "visited", "s3": "upcoming", "s4": "visited"})
        got = store.step_statuses(plan, [self.q("q1", "s3")])
        self.assertEqual(got, {"s1": "visited", "s2": "visited", "s3": "current", "s4": "upcoming"})

    def test_grade(self):
        one = {"key": ["A"]}
        many = {"key": ["A", "B"]}
        self.assertEqual(store.grade(one, ["A"]), "right")
        self.assertEqual(store.grade(one, ["B"]), "wrong")
        self.assertEqual(store.grade(one, [store.IDK]), "dontKnow")
        self.assertEqual(store.grade(many, ["B", "A"]), "right")
        self.assertEqual(store.grade(many, ["A"]), "partly")
        self.assertEqual(store.grade(many, ["A", "C"]), "partly")
        self.assertEqual(store.grade(many, ["C"]), "wrong")

    def test_confidence(self):
        self.assertEqual(store.confidence_value("fairly sure"), 70)
        self.assertEqual(store.confidence_value(" Sure "), 95)
        self.assertIsNone(store.confidence_value("Very"))
        self.assertIsNone(store.confidence_value(None))

    def test_ids(self):
        self.assertRegex(store.new_id("p_"), r"^p_[a-z0-9]{4}$")
        self.assertEqual(store.slug("!!!"), "goal")
        self.assertEqual(json.loads(json.dumps(store.now()))[-1], "Z")


if __name__ == "__main__":
    unittest.main()
