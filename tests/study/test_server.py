import io
import json
import os
import subprocess
import sys
import tempfile
import time
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

SERVER = Path(__file__).resolve().parents[2] / "plugins" / "study" / "server"
sys.path.insert(0, str(SERVER))

import store  # noqa: E402
import study_mcp  # noqa: E402

SID = "0b4c2f9e-1111-4c4c-9a9a-000000000001"
STEPS = [
    {"id": "s1", "title": "Balance", "claim": "Doing the same to both sides keeps an equation true", "dependsOn": []},
    {"id": "s2", "title": "Undo in reverse", "claim": "Undo the last operation first", "dependsOn": ["s1"]},
]


def _t(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "data"
        self.s = store.Store(self.root)
        self.srv = study_mcp.Server(self.s)
        self.opened = []
        browser = mock.patch.object(study_mcp, "open_browser", side_effect=lambda p: self.opened.append(Path(p)) or True)
        browser.start()
        self.addCleanup(browser.stop)
        quiet = mock.patch("sys.stderr", new_callable=io.StringIO)  # the expected error lines
        self.stderr = quiet.start()
        self.addCleanup(quiet.stop)
        self.addCleanup(self.tmp.cleanup)
        self.n = 0

    def rpc(self, method, params=None):
        self.n += 1
        return self.srv.handle({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params or {}})

    def call(self, name, **args):
        result = self.rpc("tools/call", {"name": name, "arguments": args})["result"]
        self.assertEqual(len(result["content"]), 1)
        self.assertEqual(result["content"][0]["type"], "text")
        return result["isError"], json.loads(result["content"][0]["text"])

    def ok(self, name, **args):
        is_error, data = self.call(name, **args)
        self.assertFalse(is_error, data)
        return data

    def bad(self, name, **args):
        is_error, data = self.call(name, **args)
        self.assertTrue(is_error, data)
        self.assertEqual(list(data), ["error"])
        return data["error"]

    def study(self, sid=SID, text="Solve ax + b = c for x and say why each step works"):
        return self.ok("start_session", session_id=sid, goal_text=text)

    def planned(self, sid=SID):
        started = self.study(sid)
        gid = started["goal"]["id"]
        self.ok("save_plan", session_id=sid, goal_id=gid, steps=STEPS)
        return gid, started["session"]["log"]

    def log(self, gid, log_id):
        return self.s.read_log(gid, log_id)

    def mc(self, sid=SID, **extra):
        args = dict(session_id=sid, kind="check", step_id="s1", question="Which keeps x + 2 = 5 true?",
                    options=["Subtract 2 from both sides", "Subtract 2 from the left"],
                    explanation="Both sides must change the same way.", key=["Subtract 2 from both sides"])
        args.update(extra)
        return args

    def props(self, *statements, origin=None):
        """Adds propositions through graph_merge; returns their ids."""
        origin = origin or {"source": self.source()}
        keys = [f"k{i}" for i in range(len(statements))]
        out = self.ok("graph_merge", origin=origin, chains=[],
                      propositions=[{"key": k, "statement": st} for k, st in zip(keys, statements)])
        return [out["ids"][k] for k in keys]

    def source(self):
        notes = Path(self.tmp.name) / "notes.md"
        if not notes.exists():
            notes.write_text("notes\n")
        return self.ok("register_source", path=str(notes))["source_id"]


class ProtocolTest(ServerTest):
    def test_initialize_negotiates_the_version(self):
        for asked in study_mcp.PROTOCOL_VERSIONS:
            result = self.rpc("initialize", {"protocolVersion": asked, "capabilities": {}})["result"]
            self.assertEqual(result["protocolVersion"], asked)
        result = self.rpc("initialize", {"protocolVersion": "2099-01-01"})["result"]
        self.assertEqual(result["protocolVersion"], study_mcp.PROTOCOL_VERSIONS[0])
        self.assertIn("tools", result["capabilities"])
        self.assertEqual(result["serverInfo"]["name"], "study")

    def test_notifications_ping_and_unknown_methods(self):
        self.assertIsNone(self.srv.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        self.assertIsNone(self.srv.handle({"jsonrpc": "2.0", "method": "notifications/whatever"}))
        self.assertEqual(self.rpc("ping")["result"], {})
        self.assertEqual(self.rpc("server/discover")["error"]["code"], -32601)
        self.assertEqual(self.rpc("resources/list")["error"]["code"], -32601)
        error = self.rpc("tools/call", {"name": "nope", "arguments": {}})["error"]
        self.assertEqual(error["code"], -32602)
        self.assertEqual(self.srv.handle_line(b"{not json")["error"]["code"], -32700)
        self.assertIsNone(self.srv.handle_line(b"{not json")["id"])
        self.assertEqual(self.srv.handle([1, 2])["error"]["code"], -32600)
        self.assertEqual(self.srv.handle({"jsonrpc": "2.0", "id": "x"})["id"], "x")

    def test_tools_list(self):
        tools = self.rpc("tools/list")["result"]["tools"]
        names = [t["name"] for t in tools]
        self.assertEqual(names, [
            "start_session", "end_session", "list_goals", "save_probe", "save_plan", "read_plan", "finish_goal",
            "pose_question", "record_verdict", "record_answer", "commit_problem", "conclude_problem", "due_list",
            "graph_overview", "graph_find", "graph_chains", "graph_merge", "register_source", "read_session",
            "open_graph_page", "open_in_browser",
        ])
        for t in tools:
            self.assertEqual(t["inputSchema"]["type"], "object")
            self.assertIs(t["inputSchema"]["additionalProperties"], False)
            self.assertTrue(t["description"])
        pose = next(t for t in tools if t["name"] == "pose_question")["inputSchema"]["properties"]
        self.assertEqual(list(pose), ["session_id", "kind", "step_id", "question", "options", "explanation",
                                      "key", "multi", "free_text"])
        self.assertNotIn("—", json.dumps(tools, ensure_ascii=False))  # no em dashes

    def test_schema_problems_are_all_listed(self):
        error = self.bad("pose_question", session_id=SID, kind="quiz", key="A", extra=1)
        for part in ("kind must be one of", "key must be a list", "question is required",
                     "explanation is required", "extra is not a known property"):
            self.assertIn(part, error)

    def test_optional_null_counts_as_left_out(self):
        self.assertEqual(self.ok("start_session", session_id=SID, goal_id=None, goal_text=None), {"goals": []})

    def test_a_bug_is_a_tool_error_and_logged(self):
        with mock.patch.object(study_mcp.Server, "tool_list_goals", side_effect=RuntimeError("boom")):
            error = self.bad("list_goals")
        self.assertIn("boom", error)
        self.assertIn("RuntimeError", (self.root / "errors.log").read_text())

    def test_newer_format_says_update_the_plugin(self):
        self.root.mkdir(parents=True)
        (self.root / "format.json").write_text('{"format": 2}')
        self.assertIn("Update the plugin", self.bad("start_session", session_id=SID, goal_text="Learn x"))


class SessionTest(ServerTest):
    def test_listing_writes_nothing(self):
        self.assertEqual(self.ok("start_session", session_id=SID), {"goals": []})
        self.assertFalse(self.root.exists())

    def test_listing_shows_unfinished_goals_newest_first(self):
        a = self.study(text="First goal")["goal"]["id"]
        b = self.study(text="Second goal")["goal"]["id"]
        c = self.study(text="Third goal")["goal"]["id"]
        self.ok("finish_goal", session_id=SID, goal_id=c, note="Held.")
        for gid, when in ((a, "2026-10-01T00:00:00Z"), (b, "2026-10-02T00:00:00Z")):
            goal = self.s.read_goal(gid)
            goal["updated"] = when
            self.s.write_json(self.s.goal_rel(gid, "goal.json"), goal)
        before = sorted(str(p) for p in self.root.rglob("*"))
        listed = self.ok("start_session", session_id="other-session")["goals"]
        self.assertEqual([g["id"] for g in listed], [b, a])
        self.assertEqual(set(listed[0]), {"id", "title", "goal", "status", "updated"})
        self.assertEqual(sorted(str(p) for p in self.root.rglob("*")), before)
        self.assertEqual([g["id"] for g in self.ok("list_goals")["goals"]][1:], [b, a])
        self.assertEqual(set(self.ok("list_goals")["goals"][0]), {"id", "title", "goal", "status", "updated", "doneAt"})

    def test_creating_a_goal(self):
        out = self.study(text="Solve ax + b = c for x and say why each step works")
        goal = out["goal"]
        self.assertEqual(goal["title"], "Solve ax + b = c")
        self.assertEqual(goal["status"], "probing")
        self.assertTrue(goal["id"].startswith("solve-ax-b-c-"))
        self.assertEqual(list(goal), ["id", "title", "goal", "status", "probe", "created", "updated", "doneAt"])
        self.assertEqual(out["session"]["mode"], "study")
        self.assertIsNone(out["plan"])
        self.assertEqual(out["lastSitting"], [])
        self.assertEqual(out["graph"]["propositions"], 0)
        self.assertEqual(Path(out["paths"]["goal"]), (self.root / "goals" / goal["id"]).absolute())
        self.assertTrue(Path(out["paths"]["media"]).is_dir())
        marker = self.s.read_json(f"active/{SID}.json")
        self.assertEqual({k: marker[k] for k in ("mode", "goal", "log")},
                         {"mode": "study", "goal": goal["id"], "log": out["session"]["log"]})
        store.parse_time(marker["started"])
        start = self.log(goal["id"], out["session"]["log"])
        self.assertEqual([(e["type"], e["claudeSession"], e["goal"]) for e in start], [("start", SID, goal["id"])])
        titled = self.ok("start_session", session_id=SID, goal_text="Long text here", title="Short")["goal"]
        self.assertEqual(titled["title"], "Short")

    def test_opening_a_goal_returns_the_last_sitting(self):
        gid, first_log = self.planned()
        earlier = self.s.path(self.s.log_rel(gid, first_log))
        lines = [json.loads(line) for line in earlier.read_text().splitlines()]
        for line in lines:
            line["at"] = "2026-10-01T00:00:00Z"  # log ids sort by the first entry's time
        earlier.write_text("".join(json.dumps(line) + "\n" for line in lines))
        self.ok("pose_question", **self.mc())
        out = self.ok("start_session", session_id=SID, goal_id=gid)
        self.assertNotEqual(out["session"]["log"], first_log)
        self.assertEqual([e["type"] for e in out["lastSitting"]], ["start", "plan", "question"])
        self.assertEqual(out["plan"]["steps"][0]["status"], "current")
        self.assertEqual(self.s.read_marker(SID)["log"], out["session"]["log"])
        self.assertEqual(self.ok("read_session", goal_id=gid)["log"], out["session"]["log"])
        self.assertEqual(self.ok("read_session", goal_id=gid, log_id=first_log)["entries"][0]["type"], "start")

    def test_argument_conflicts(self):
        gid = self.study()["goal"]["id"]
        error = self.bad("start_session", session_id=SID, goal_text="x", goal_id=gid, topic="t")
        self.assertIn("not both", error)
        self.assertIn("topic is for practice", error)
        self.assertIn("title only goes with goal_text", self.bad("start_session", session_id=SID, title="x"))
        self.assertIn("No goal", self.bad("start_session", session_id=SID, goal_id="missing-abcd"))
        error = self.bad("start_session", session_id=SID, mode="practice", goal_id=gid, title="x")
        self.assertIn("goal_id is for study", error)
        self.assertIn("title is for study", error)
        self.assertIn("not valid", self.bad("start_session", session_id="../x"))

    def test_practice(self):
        a, b, c = self.props("Subtracting the same number from both sides keeps an equation true",
                             "Dividing both sides by the same nonzero number keeps it true",
                             "A derivative measures a rate of change")
        self.ok("graph_merge", origin={"source": self.source()}, propositions=[],
                chains=[{"premises": [a, b], "conclusion": c}])
        out = self.ok("start_session", session_id=SID, mode="practice", topic="both sides")
        self.assertEqual(out["session"]["mode"], "practice")
        self.assertEqual(out["due"], [])
        self.assertEqual([p["id"] for p in out["candidates"]["propositions"]], [a, b])
        self.assertEqual(out["candidates"]["chains"][0]["conclusion"]["id"], c)
        self.assertTrue(Path(out["paths"]["media"]).is_dir())
        marker = self.s.read_marker(SID)
        self.assertEqual((marker["mode"], marker["goal"]), ("practice", None))
        entries = self.s.read_log(None, out["session"]["log"])
        self.assertEqual([(e["type"], e["goal"]) for e in entries], [("start", None)])
        everything = self.ok("start_session", session_id=SID, mode="practice")
        self.assertEqual(len(everything["candidates"]["propositions"]), 3)
        self.assertEqual(self.ok("start_session", session_id=SID, mode="practice", topic="nothing like it")
                         ["candidates"], {"propositions": [], "chains": []})

    def test_end_session(self):
        out = self.study()
        self.assertEqual(self.ok("end_session", session_id=SID), {"ended": out["session"]["log"]})
        self.assertFalse((self.root / "active" / f"{SID}.json").exists())
        self.assertEqual(self.log(out["goal"]["id"], out["session"]["log"])[-1]["type"], "end")
        self.assertEqual(self.ok("end_session", session_id=SID), {"ended": None})

    def test_tools_need_a_live_marker(self):
        gid, log_id = self.planned()
        self.ok("end_session", session_id=SID)
        calls = {
            "save_probe": dict(goal_id=gid, strands=[{"name": "n", "floor": "", "ceiling": "", "buildFrom": ""}], summary="s"),
            "save_plan": dict(goal_id=gid, steps=STEPS),
            "finish_goal": dict(goal_id=gid, note="n"),
            "pose_question": self.mc(),
            "record_verdict": dict(question_id="q1", verdict="right"),
            "record_answer": dict(question_id="q1", text="t"),
            "commit_problem": dict(statement="s", mode="recall", targets=["p_x"], cue_class="c", solution="s"),
            "conclude_problem": dict(problem_id="pr_x", outcome="solved", verdict="right", rung=None, retest=False),
        }
        for name, args in calls.items():
            args = dict(args, session_id=SID)
            self.assertIn("call start_session", self.bad(name, **args), name)

    def test_a_stale_marker_counts_as_none(self):
        out = self.study()
        old = time.time() - store.MARKER_TTL - 60
        marker = self.s.read_json(f"active/{SID}.json")
        marker["started"] = _t(datetime.fromtimestamp(old, timezone.utc))
        self.s.write_json(f"active/{SID}.json", marker)
        for rel in (f"active/{SID}.json", self.s.log_rel(out["goal"]["id"], out["session"]["log"])):
            os.utime(self.s.path(rel), (old, old))
        self.assertIn("call start_session", self.bad("pose_question", **self.mc()))
        self.assertEqual(self.ok("end_session", session_id=SID), {"ended": None})
        self.assertFalse((self.root / "active" / f"{SID}.json").exists())

    def test_wrong_goal_or_mode(self):
        gid, _ = self.planned()
        self.assertIn("is studying", self.bad("save_plan", session_id=SID, goal_id="other-abcd", steps=STEPS))
        self.ok("start_session", session_id=SID, mode="practice")
        self.assertIn("this session is practice", self.bad("save_plan", session_id=SID, goal_id=gid, steps=STEPS))
        self.assertIn("this session is practice", self.bad("pose_question", **self.mc()))


class GoalTest(ServerTest):
    def strands(self):
        return [{"name": "Inverse operations", "floor": "Undoes + with -", "ceiling": "Undoes 2x + 3",
                 "misconceptions": ["Only the left side changes"], "buildFrom": "Balance scales"}]

    def test_save_probe(self):
        out = self.study()
        gid = out["goal"]["id"]
        goal = self.ok("save_probe", session_id=SID, goal_id=gid, strands=self.strands(), summary="Holds + and -.",
                       goal="Solve 2x + 3 = 11 and say why", title="Two-step equations")["goal"]
        self.assertEqual(goal["status"], "planning")
        self.assertEqual((goal["goal"], goal["title"]), ("Solve 2x + 3 = 11 and say why", "Two-step equations"))
        self.assertEqual(goal["probe"], {"strands": self.strands(), "summary": "Holds + and -."})
        self.assertEqual(self.s.read_goal(gid), goal)
        self.assertEqual(self.log(gid, out["session"]["log"])[-1]["type"], "probe")
        bare = self.ok("save_probe", session_id=SID, goal_id=gid, summary="s",
                       strands=[{"name": "n", "floor": "f", "ceiling": "c", "buildFrom": "b"}])["goal"]
        self.assertEqual(bare["probe"]["strands"][0]["misconceptions"], [])

    def test_save_probe_refused_while_a_question_is_open(self):
        out = self.study()
        gid = out["goal"]["id"]
        self.ok("pose_question", session_id=SID, kind="probe", question="What is x if x + 2 = 5?",
                free_text=True, explanation="Subtract 2.", key=["3"])
        error = self.bad("save_probe", session_id=SID, goal_id=gid, strands=self.strands(), summary="s")
        self.assertIn("q1 is still open", error)
        self.s.append_log(gid, out["session"]["log"], {"type": "answer", "question": "q1", "freeText": "3"})
        self.ok("save_probe", session_id=SID, goal_id=gid, strands=self.strands(), summary="s")

    def test_save_plan_checks(self):
        gid = self.study()["goal"]["id"]
        steps = [
            {"id": "s1", "title": "a", "claim": "a", "dependsOn": ["s3"]},
            {"id": "s2", "title": "b", "claim": "b", "dependsOn": ["s1", "s9"]},
            {"id": "s3", "title": "c", "claim": "c", "dependsOn": ["s2"]},
            {"id": "s2", "title": "d", "claim": "d", "dependsOn": []},
            {"id": "s4", "title": "e", "claim": "e", "dependsOn": ["s4"]},
        ]
        error = self.bad("save_plan", session_id=SID, goal_id=gid, steps=steps)
        self.assertIn("'s2' is used twice", error)
        self.assertIn("depends on 's9', which is not a step", error)
        self.assertIn("'s4' depends on itself", error)
        self.assertIn("form a loop: s1 -> s3 -> s2 -> s1", error)
        self.assertIsNone(self.s.read_plan(gid))
        self.assertIn("steps must have at least 1 item", self.bad("save_plan", session_id=SID, goal_id=gid, steps=[]))

    def test_save_plan_bumps_the_version(self):
        out = self.study()
        gid = out["goal"]["id"]
        first = self.ok("save_plan", session_id=SID, goal_id=gid, steps=STEPS)["plan"]
        self.assertEqual(first["version"], 1)
        self.assertEqual([s["status"] for s in first["steps"]], ["upcoming", "upcoming"])
        second = self.ok("save_plan", session_id=SID, goal_id=gid, steps=STEPS[:1])["plan"]
        self.assertEqual(second["version"], 2)
        self.assertEqual(self.s.read_plan(gid)["steps"], STEPS[:1])
        plans = [e for e in self.log(gid, out["session"]["log"]) if e["type"] == "plan"]
        self.assertEqual([e["version"] for e in plans], [1, 2])

    def test_read_plan_statuses(self):
        gid, _ = self.planned()
        self.assertEqual(self.ok("read_plan", goal_id=gid)["plan"]["steps"][0]["status"], "upcoming")
        self.ok("pose_question", **self.mc(step_id="s2"))
        statuses = [s["status"] for s in self.ok("read_plan", goal_id=gid)["plan"]["steps"]]
        self.assertEqual(statuses, ["visited", "current"])
        other = self.study(text="Another goal")["goal"]["id"]
        self.assertEqual(self.ok("read_plan", goal_id=other), {"plan": None})
        self.assertIn("No goal", self.bad("read_plan", goal_id="missing-abcd"))

    def test_finish_goal(self):
        gid, log_id = self.planned()
        goal = self.ok("finish_goal", session_id=SID, goal_id=gid, note="It feels obvious now.")["goal"]
        self.assertEqual(goal["status"], "done")
        store.parse_time(goal["doneAt"])
        self.assertEqual(self.log(gid, log_id)[-1], dict(self.log(gid, log_id)[-1], type="end", note="It feels obvious now."))
        self.assertIsNone(self.s.read_json(f"active/{SID}.json"))


class QuestionTest(ServerTest):
    def test_multiple_choice_checks(self):
        self.planned()
        error = self.bad("pose_question", **self.mc(options=["A", "a ", "B"], key=["A", "C"]))
        self.assertIn("option 'a' is listed twice", error)
        self.assertIn("key 'C' is not one of the options", error)
        self.assertIn("several labels, so set multi true", error)
        self.assertIn("must have 2 to 4 items", self.bad("pose_question", **self.mc(options=["A"], key=["A"])))
        self.assertIn("must have 2 to 4 items",
                      self.bad("pose_question", **self.mc(options=["A", "B", "C", "D", "E"], key=["A"])))
        self.assertIn("leave \"I don't know\" out",
                      self.bad("pose_question", **self.mc(options=["A", "I don't know"], key=["A"])))
        self.assertIn("needs 2 to 4 options", self.bad("pose_question", **self.mc(options=None)))
        self.assertIn("options[1] must not be empty", self.bad("pose_question", **self.mc(options=["A", " "], key=["A"])))
        self.assertIn("key lists a label twice", self.bad("pose_question", **self.mc(options=["A", "B"], key=["A", "A"], multi=True)))

    def test_steps_by_kind(self):
        self.planned()
        for kind in ("predict", "check"):
            self.assertIn(f"a {kind} question needs step_id", self.bad("pose_question", **self.mc(kind=kind, step_id=None)))
        self.assertIn("probe question has no step", self.bad("pose_question", **self.mc(kind="probe")))
        self.assertIn("'s7' is not a plan step", self.bad("pose_question", **self.mc(step_id="s7")))
        self.ok("pose_question", **self.mc(kind="probe", step_id=None))
        self.ok("pose_question", **self.mc(kind="predict"))

    def test_step_before_a_plan(self):
        self.study()
        self.assertIn("call save_plan first", self.bad("pose_question", **self.mc()))

    def test_free_text_checks(self):
        self.planned()
        error = self.bad("pose_question", **self.mc(free_text=True, multi=True, key=["a", "b"]))
        self.assertIn("free-text question has no options", error)
        self.assertIn("can't be multi", error)
        self.assertIn("one-item list", error)

    def test_options_shuffled_with_i_dont_know(self):
        gid, log_id = self.planned()
        out = self.ok("pose_question", **self.mc(options=["A", "B", "C"], key=["A", "C"], multi=True))
        self.assertEqual(out["question_id"], "q1")
        self.assertEqual(sorted(out["options"]), sorted(["A", "B", "C", store.IDK]))
        entry = self.log(gid, log_id)[-1]
        self.assertEqual(entry["type"], "question")
        self.assertEqual((entry["options"], entry["key"], entry["multi"], entry["freeText"]),
                         (out["options"], ["A", "C"], True, False))
        self.assertEqual(entry["explanation"], "Both sides must change the same way.")
        self.assertEqual(list(entry)[:3], ["n", "at", "type"])
        four = self.ok("pose_question", **self.mc(options=["A", "B", "C", "D"], key=["B"]))
        self.assertEqual(sorted(four["options"]), ["A", "B", "C", "D"])
        orders = {tuple(self.ok("pose_question", **self.mc(options=["A", "B", "C", "D"], key=["B"]))["options"])
                  for _ in range(30)}
        self.assertGreater(len(orders), 1)

    def test_single_key_may_be_multi(self):
        self.planned()
        self.ok("pose_question", **self.mc(options=["A", "B", "C"], key=["A"], multi=True))

    def test_second_question_closes_the_first(self):
        gid, log_id = self.planned()
        first = self.ok("pose_question", **self.mc())
        self.assertNotIn("closed", first)
        second = self.ok("pose_question", session_id=SID, kind="check", step_id="s1", question="Why?",
                         free_text=True, explanation="e", key=["Because both sides change alike"])
        self.assertEqual((second["question_id"], second["closed"]), ("q2", "q1"))
        self.assertNotIn("options", second)
        entries = self.log(gid, log_id)
        verdict = entries[-2]
        self.assertEqual({k: verdict[k] for k in ("type", "question", "verdict", "by")},
                         {"type": "verdict", "question": "q1", "verdict": "skipped", "by": "server"})
        self.assertEqual((entries[-1]["options"], entries[-1]["freeText"]), (None, True))
        self.assertEqual(store.open_question(entries)["id"], "q2")
        self.s.append_log(gid, log_id, {"type": "answer", "question": "q2", "freeText": "x"})
        self.assertNotIn("closed", self.ok("pose_question", **self.mc()))

    def test_first_stepped_question_sets_teaching(self):
        gid, _ = self.planned()
        self.ok("pose_question", **self.mc(kind="probe", step_id=None))
        self.assertEqual(self.s.read_goal(gid)["status"], "probing")
        self.ok("pose_question", **self.mc())
        self.assertEqual(self.s.read_goal(gid)["status"], "teaching")

    def test_record_verdict_and_answer(self):
        gid, log_id = self.planned()
        self.ok("pose_question", session_id=SID, kind="check", step_id="s1", question="Why?", free_text=True,
                explanation="e", key=["model"])
        self.assertEqual(self.ok("record_answer", session_id=SID, question_id="q1", text="Both sides", confidence=70),
                         {"question_id": "q1"})
        answer = self.log(gid, log_id)[-1]
        self.assertEqual((answer["type"], answer["question"], answer["freeText"], answer["confidence"]),
                         ("answer", "q1", "Both sides", 70))
        out = self.ok("record_verdict", session_id=SID, question_id="q1", verdict="partly", note="No reason given.")
        self.assertEqual(out, {"question_id": "q1", "verdict": "partly"})
        verdict = self.log(gid, log_id)[-1]
        self.assertEqual({k: verdict[k] for k in ("type", "question", "verdict", "by", "note", "confidence")},
                         {"type": "verdict", "question": "q1", "verdict": "partly", "by": "teacher",
                          "note": "No reason given.", "confidence": None})
        self.ok("record_verdict", session_id=SID, question_id="q1", verdict="right", confidence=95)
        error = self.bad("record_verdict", session_id=SID, question_id="q1", verdict="skipped", confidence=50)
        self.assertIn("verdict must be one of", error)
        self.assertIn("confidence must be one of 10, 40, 70, 95", error)
        self.assertIn("No question 'q9'", self.bad("record_verdict", session_id=SID, question_id="q9", verdict="right"))
        self.assertIn("No question 'q9'", self.bad("record_answer", session_id=SID, question_id="q9", text="t"))


class PracticeTest(ServerTest):
    def practice(self):
        a, b = self.props("Subtracting the same number from both sides keeps an equation true",
                          "Undo the last operation first")
        log_id = self.ok("start_session", session_id=SID, mode="practice")["session"]["log"]
        return a, b, log_id

    def commit(self, targets, **extra):
        args = dict(session_id=SID, statement="Solve 3x + 4 = 19.", mode="recall", targets=targets,
                    cue_class="weak", solution="Subtract 4, then divide by 3: x = 5.")
        args.update(extra)
        return self.ok("commit_problem", **args)["problem_id"]

    def test_commit_and_conclude(self):
        a, b, log_id = self.practice()
        pid = self.commit([a, b])
        self.assertTrue(pid.startswith("pr_"))
        lines = self.s.read_jsonl("practice/problems.jsonl")
        self.assertEqual({k: lines[0][k] for k in ("type", "id", "log", "targets", "cueClass")},
                         {"type": "commit", "id": pid, "log": log_id, "targets": [a, b], "cueClass": "weak"})
        self.assertEqual(self.s.read_log(None, log_id)[-1]["problem"], pid)
        out = self.ok("conclude_problem", session_id=SID, problem_id=pid, outcome="solvedWithHints", verdict="right",
                      rung="R1", retest=False)
        self.assertEqual(out["solution"], "Subtract 4, then divide by 3: x = 5.")
        self.assertEqual([d["target"] for d in out["due"]], [a, b])
        due = store.parse_time(out["due"][0]["due"]) - datetime.now(timezone.utc)
        self.assertAlmostEqual(due.total_seconds(), 3 * 86400, delta=120)
        conclude = self.s.read_jsonl("practice/problems.jsonl")[-1]
        self.assertEqual({k: conclude[k] for k in ("type", "id", "outcome", "rung", "missClass", "retest")},
                         {"type": "conclude", "id": pid, "outcome": "solvedWithHints", "rung": "R1",
                          "missClass": None, "retest": False})
        entry = self.s.read_log(None, log_id)[-1]
        self.assertEqual({k: entry[k] for k in ("type", "problem", "outcome", "verdict")},
                         {"type": "conclude", "problem": pid, "outcome": "solvedWithHints", "verdict": "right"})
        self.assertIn("already concluded", self.bad("conclude_problem", session_id=SID, problem_id=pid, outcome="solved",
                                                    verdict="right", rung=None, retest=False))

    def test_commit_refused_while_a_problem_is_open(self):
        a, _, _ = self.practice()
        first = self.commit([a])
        error = self.bad("commit_problem", session_id=SID, statement="s", mode="recall", targets=[a],
                         cue_class="c", solution="s")
        self.assertIn(f"problem {first} is still open", error)
        self.ok("conclude_problem", session_id=SID, problem_id=first, outcome="movedOn", verdict="wrong", rung="R4",
                miss_class="cue", retest=True)
        self.commit([a])

    def test_commit_checks(self):
        a, _, _ = self.practice()
        error = self.bad("commit_problem", session_id=SID, statement="s", mode="guess", targets=[a, a, "p_zzzz"],
                         cue_class="c", solution="s")
        self.assertIn("mode must be one of", error)
        error = self.bad("commit_problem", session_id=SID, statement="s", mode="recall", targets=[a, a, "p_zzzz"],
                         cue_class="c", solution="s")
        self.assertIn("'p_zzzz' is not a proposition or chain id", error)
        self.assertIn("lists an id twice", error)

    def test_conclude_checks(self):
        a, _, _ = self.practice()
        pid = self.commit([a])
        error = self.bad("conclude_problem", session_id=SID, problem_id=pid, outcome="solved", verdict="right",
                         rung="R2", retest=False)
        self.assertIn("solved means no hint", error)
        error = self.bad("conclude_problem", session_id=SID, problem_id=pid, outcome="solvedWithHints",
                         verdict="right", rung=None, retest=False)
        self.assertIn("needs rung", error)
        self.assertIn("No problem", self.bad("conclude_problem", session_id=SID, problem_id="pr_none", outcome="solved",
                                             verdict="right", rung=None, retest=False))
        self.assertIn("rung is required", self.bad("conclude_problem", session_id=SID, problem_id=pid,
                                                   outcome="solved", verdict="right", retest=False))
        self.ok("start_session", session_id=SID, mode="practice")
        self.assertIn("not this session's", self.bad("conclude_problem", session_id=SID, problem_id=pid,
                                                     outcome="solved", verdict="right", rung=None, retest=False))

    def test_problems_are_practice_only(self):
        a = self.props("An idea")[0]
        self.study()
        error = self.bad("commit_problem", session_id=SID, statement="s", mode="recall", targets=[a],
                         cue_class="c", solution="s")
        self.assertIn("works in practice sessions", error)


class DueTest(ServerTest):
    def history(self, target, concludes, start=None):
        """Writes one problem per conclude for `target`; each conclude is (days after start, fields).

        A `mode` in fields goes on the commit instead (default recall).
        """
        start = start or datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i, (day, fields) in enumerate(concludes):
            pid = f"pr_{target[-4:]}{i}"
            at = _t(start + timedelta(days=day))
            fields = dict(fields)
            mode = fields.pop("mode", "recall")
            self.s.append_jsonl("practice/problems.jsonl", {"type": "commit", "id": pid, "at": at, "log": "l",
                                                           "mode": mode, "targets": [target], "solution": "s"})
            self.s.append_jsonl("practice/problems.jsonl", dict({"type": "conclude", "id": pid, "at": at,
                                                                 "rung": None, "retest": False}, **fields))
        return study_mcp.due_state(self.s)[target]

    def test_one_day(self):
        for fields in ({"outcome": "movedOn"}, {"outcome": "surrendered"},
                       {"outcome": "solvedWithHints", "rung": "R3"}, {"outcome": "solvedWithHints", "rung": "R5"},
                       {"outcome": "solved", "retest": True}):
            self.assertEqual(study_mcp.gap_days(fields, 40), 1, fields)

    def test_three_days_with_low_hints(self):
        for rung in ("R0", "R1", "R2"):
            self.assertEqual(study_mcp.gap_days({"outcome": "solvedWithHints", "rung": rung}, 40), 3)

    def test_clean_solves_double_between_3_and_60(self):
        solved = {"outcome": "solved"}
        state = self.history("p_aaaa", [(0, solved)])
        self.assertEqual(state["gap"], 3)
        self.assertEqual(state["due"], datetime(2026, 1, 4, tzinfo=timezone.utc))
        gaps = [self.history(f"p_b{i:03d}", [(d, solved) for d in range(i + 1)])["gap"] for i in range(7)]
        self.assertEqual(gaps, [3, 6, 12, 24, 48, 60, 60])
        after_miss = self.history("p_cccc", [(0, solved), (3, solved), (9, {"outcome": "movedOn"}), (10, solved)])
        self.assertEqual(after_miss["gap"], 3)
        after_hints = self.history("p_dddd", [(0, {"outcome": "solvedWithHints", "rung": "R2"}), (3, solved)])
        self.assertEqual(after_hints["gap"], 6)
        self.assertEqual(after_hints["outcome"], "solved")

    def test_due_list(self):
        a, b, c, d = self.props("Idea a", "Idea b", "Idea c", "Idea d")
        now = datetime.now(timezone.utc)
        self.history(a, [(0, {"outcome": "solved"}), (1, {"outcome": "movedOn", "mode": "discrimination"})],
                     start=now - timedelta(days=6))
        self.history(b, [(0, {"outcome": "surrendered"})], start=now - timedelta(days=2))
        self.history(c, [(0, {"outcome": "solved"})], start=now - timedelta(days=2))  # due in 1 day
        self.history("p_gone", [(0, {"outcome": "movedOn"})], start=now - timedelta(days=5))
        due = self.ok("due_list")["due"]
        self.assertEqual([x["target"] for x in due], [a, b])  # longest overdue first; d never practiced
        self.assertEqual(set(due[0]), {"target", "statement", "due", "lastOutcome", "lastMode"})
        self.assertEqual((due[0]["statement"], due[0]["lastOutcome"], due[0]["lastMode"]),
                         ("Idea a", "movedOn", "discrimination"))  # the latest problem's
        self.assertEqual(due[1]["lastMode"], "recall")
        self.assertEqual([x["target"] for x in self.ok("due_list", limit=1)["due"]], [a])
        self.assertIn("at least 1", self.bad("due_list", limit=0))
        self.assertEqual(self.ok("start_session", session_id=SID, mode="practice")["due"], due)

    def test_chain_targets(self):
        a, b = self.props("Idea a", "Idea b")
        self.ok("graph_merge", origin={"source": self.source()}, propositions=[],
                chains=[{"premises": [a], "conclusion": b}])
        cid = next(iter(self.s.graph()[1]))
        self.history(cid, [(0, {"outcome": "movedOn"})], start=datetime.now(timezone.utc) - timedelta(days=2))
        self.assertEqual(self.ok("due_list")["due"][0]["statement"], "Idea a -> Idea b")

    def test_candidates_carry_the_last_practice(self):
        a, b = self.props("Idea a", "Idea b")
        self.ok("graph_merge", origin={"source": self.source()}, propositions=[],
                chains=[{"premises": [a], "conclusion": b}])
        cid = next(iter(self.s.graph()[1]))
        self.history(a, [(0, {"outcome": "solved", "mode": "discrimination"})], start=datetime.now(timezone.utc))
        self.history(cid, [(0, {"outcome": "movedOn", "mode": "composition"})], start=datetime.now(timezone.utc))
        out = self.ok("start_session", session_id=SID, mode="practice")
        self.assertEqual(out["due"], [])  # practiced, but not due yet
        props = {p["id"]: p for p in out["candidates"]["propositions"]}
        self.assertEqual(props[a], {"id": a, "statement": "Idea a", "lastMode": "discrimination", "lastOutcome": "solved"})
        self.assertEqual((props[b]["lastMode"], props[b]["lastOutcome"]), (None, None))  # never practiced
        chain = out["candidates"]["chains"][0]
        self.assertEqual(set(chain), {"id", "premises", "conclusion", "lastMode", "lastOutcome"})
        self.assertEqual((chain["lastMode"], chain["lastOutcome"]), ("composition", "movedOn"))
        self.assertEqual(set(self.ok("graph_chains")["chains"][0]), {"id", "premises", "conclusion"})


class GraphTest(ServerTest):
    def setUp(self):
        super().setUp()
        self.started = self.study()
        self.gid = self.started["goal"]["id"]
        self.log_id = self.started["session"]["log"]
        self.ok("save_plan", session_id=SID, goal_id=self.gid, steps=STEPS)
        self.origin = {"goal": self.gid, "log": self.log_id, "step": "s1"}

    def merge(self, propositions, chains=(), origin=None):
        return self.ok("graph_merge", origin=origin or self.origin, propositions=propositions, chains=list(chains))

    def lines(self, name):
        return self.s.read_jsonl(f"graph/{name}.jsonl")

    def test_adds_and_logs_extracted(self):
        out = self.merge([{"key": "a", "statement": "Subtracting the same number from both sides keeps it true"},
                          {"key": "b", "statement": "x + 2 = 5 means x = 3"}],
                         [{"premises": ["a"], "conclusion": "b"}])
        self.assertEqual(out["added"], {"propositions": 2, "chains": 1})
        self.assertEqual(out["linked"], 0)
        props, chains = self.s.graph()
        self.assertEqual(props[out["ids"]["a"]]["sources"], [self.origin])
        chain = next(iter(chains.values()))
        self.assertEqual((chain["premises"], chain["conclusion"]), ([out["ids"]["a"]], out["ids"]["b"]))
        extracted = self.log(self.gid, self.log_id)[-1]
        self.assertEqual({k: extracted[k] for k in ("type", "step", "propositions", "chains")},
                         {"type": "extracted", "step": "s1", "propositions": [out["ids"]["a"], out["ids"]["b"]],
                          "chains": [chain["id"]]})

    def test_dedupe_by_text_alias_and_same_as(self):
        first = self.merge([{"key": "a", "statement": "Both sides change alike"},
                            {"key": "b", "statement": "Undo the last step first"}])["ids"]
        self.s.append_jsonl("graph/propositions.jsonl", {"op": "alias", "id": first["b"], "text": "Reverse order undoes"})
        origin2 = {"goal": self.gid, "log": self.log_id, "step": "s2"}
        out = self.merge([
            {"key": "x", "statement": "  both SIDES   change alike "},   # exact text, case and spacing ignored
            {"key": "y", "statement": "reverse order undoes"},           # an alias
            {"key": "z", "statement": "Whatever happens to one side happens to the other", "same_as": first["a"]},
            {"key": "w", "statement": "Undo the last step first", "same_as": first["b"]},  # same wording: no alias
            {"key": "v", "statement": "A new idea"},
            {"key": "u", "statement": "a new  idea"},                    # a duplicate inside the call
        ], origin=origin2)
        self.assertEqual(out["ids"], {"x": first["a"], "y": first["b"], "z": first["a"], "w": first["b"],
                                      "v": out["ids"]["v"], "u": out["ids"]["v"]})
        self.assertEqual(out["added"], {"propositions": 1, "chains": 0})
        self.assertEqual(out["linked"], 2)
        props, _ = self.s.graph()
        self.assertEqual(props[first["a"]]["aliases"], ["Whatever happens to one side happens to the other"])
        self.assertEqual(props[first["b"]]["aliases"], ["Reverse order undoes"])
        self.assertEqual(props[first["a"]]["sources"], [self.origin, origin2])
        self.assertEqual(props[first["b"]]["sources"], [self.origin, origin2])
        again = self.merge([{"key": "x", "statement": "Both sides change alike"}], origin=origin2)
        self.assertEqual(again["linked"], 1)
        self.assertEqual(self.s.graph()[0][first["a"]]["sources"], [self.origin, origin2])  # no repeat source

    def test_duplicate_chains(self):
        ids = self.merge([{"key": "a", "statement": "A"}, {"key": "b", "statement": "B"}, {"key": "c", "statement": "C"}],
                         [{"premises": ["a", "b"], "conclusion": "c"}])["ids"]
        source = {"source": self.source()}
        out = self.merge([], [{"premises": [ids["b"], ids["a"]], "conclusion": ids["c"]},
                              {"premises": [ids["a"]], "conclusion": ids["c"]},
                              {"premises": [ids["a"]], "conclusion": ids["c"]}], origin=source)
        self.assertEqual(out["added"], {"propositions": 0, "chains": 1})
        self.assertEqual(out["linked"], 1)
        chains = self.s.graph()[1]
        self.assertEqual(len(chains), 2)
        first = next(c for c in chains.values() if len(c["premises"]) == 2)
        self.assertEqual(first["sources"], [self.origin, source])
        self.assertEqual(self.log(self.gid, self.log_id)[-1]["type"], "extracted")  # a source origin logs nothing

    def test_unknown_ids_write_nothing(self):
        before = self.lines("propositions")
        error = self.bad("graph_merge", origin=self.origin, propositions=[
            {"key": "a", "statement": "A"},
            {"key": "a", "statement": "A again"},
            {"key": "b", "statement": "B", "same_as": "p_none"},
            {"key": "p_x", "statement": "C"},
        ], chains=[
            {"premises": ["a", "zz"], "conclusion": "b"},
            {"premises": ["a"], "conclusion": "a"},
            {"premises": ["a", "a"], "conclusion": "p_gone"},
        ])
        for part in ("'a' is used twice", "same_as 'p_none' is not a proposition id", "'p_x' starts like an id",
                     "chains[0].premises[1] 'zz' is neither", "chains[1]: the conclusion is also a premise",
                     "chains[2].conclusion 'p_gone' is neither"):
            self.assertIn(part, error)
        self.assertNotIn("chains[0].conclusion", error)  # b had a bad same_as: said once
        self.assertEqual(self.lines("propositions"), before)
        self.assertEqual(self.lines("chains"), [])

    def test_origin_checks(self):
        p = [{"key": "a", "statement": "A"}]
        self.assertIn("origin must be", self.bad("graph_merge", origin={"goal": self.gid}, propositions=p, chains=[]))
        self.assertIn("not registered", self.bad("graph_merge", origin={"source": "src_none"}, propositions=p, chains=[]))
        self.assertIn("is not a goal", self.bad("graph_merge", origin=dict(self.origin, goal="nope-abcd"),
                                                propositions=p, chains=[]))
        self.assertIn("is not a session log", self.bad("graph_merge", origin=dict(self.origin, log="2026-01-01-zzzz"),
                                                       propositions=p, chains=[]))
        self.assertIn("is not a step", self.bad("graph_merge", origin=dict(self.origin, step="s9"),
                                                propositions=p, chains=[]))

    def test_find_chains_and_overview(self):
        ids = self.merge([{"key": "a", "statement": "Subtracting from both sides keeps balance"},
                          {"key": "b", "statement": "Dividing both sides keeps balance"},
                          {"key": "c", "statement": "x = 3"}],
                         [{"premises": ["a"], "conclusion": "c"}, {"premises": ["b"], "conclusion": "c"}])["ids"]
        self.s.append_jsonl("graph/propositions.jsonl", {"op": "alias", "id": ids["c"], "text": "The answer is three"})
        found = lambda pattern: [m["id"] for m in self.ok("graph_find", pattern=pattern)["matches"]]
        self.assertEqual(found("BOTH SIDES"), [ids["a"], ids["b"]])
        self.assertEqual(found("both sides"), found("*both sides*"))
        self.assertEqual(found("subtract*balance"), [ids["a"]])
        self.assertEqual(found("both*"), [])  # with *, the whole text must match
        self.assertEqual(found("*three"), [ids["c"]])
        self.assertEqual(found("x.=.3"), [])  # no regex
        self.assertEqual(self.ok("graph_find", pattern="*three")["matches"][0]["aliases"], ["The answer is three"])
        self.assertIn("must not be empty", self.bad("graph_find", pattern="  "))
        self.assertEqual(len(self.ok("graph_chains")["chains"]), 2)
        by_a = self.ok("graph_chains", node_id=ids["a"])["chains"]
        self.assertEqual(by_a[0]["premises"], [{"id": ids["a"], "statement": "Subtracting from both sides keeps balance"}])
        self.assertEqual(by_a[0]["conclusion"], {"id": ids["c"], "statement": "x = 3"})
        self.assertEqual(len(self.ok("graph_chains", node_id=ids["c"])["chains"]), 2)
        self.assertIn("not a proposition id", self.bad("graph_chains", node_id="p_none"))
        other = self.ok("start_session", session_id="s-2", goal_text="Other goal")
        overview = self.ok("graph_overview")
        self.assertEqual((overview["propositions"], overview["chains"], overview["byGoal"]), (3, 2, {self.gid: 3}))
        self.assertEqual(self.ok("graph_overview", goal_id=other["goal"]["id"])["byGoal"], {self.gid: 3})
        self.assertIn("No goal", self.bad("graph_overview", goal_id="missing-abcd"))

    def test_overview_puts_the_goal_first_and_caps(self):
        other = self.ok("start_session", session_id="s-2", goal_text="Other goal")
        self.ok("save_plan", session_id="s-2", goal_id=other["goal"]["id"], steps=STEPS)
        self.merge([{"key": f"k{i}", "statement": f"Idea {i}"} for i in range(45)])
        mine = self.merge([{"key": "m", "statement": "Mine"}],
                          origin={"goal": other["goal"]["id"], "log": other["session"]["log"], "step": "s2"})["ids"]["m"]
        overview = self.ok("graph_overview", goal_id=other["goal"]["id"])
        self.assertEqual(len(overview["statements"]), 40)
        self.assertEqual(overview["statements"][0], {"id": mine, "statement": "Mine"})
        self.assertEqual(overview["byGoal"], {self.gid: 45, other["goal"]["id"]: 1})


class SourceAndPageTest(ServerTest):
    def test_register_source(self):
        notes = Path(self.tmp.name) / "notes.md"
        notes.write_text("one\n")
        first = self.ok("register_source", path=str(notes))
        self.assertTrue(first["source_id"].startswith("src_"))
        self.assertTrue(first["changed"])
        self.assertEqual(first["path"], str(notes.resolve()))
        same = self.ok("register_source", path=str(notes))
        self.assertEqual((same["source_id"], same["changed"]), (first["source_id"], False))
        notes.write_text("two\n")
        edited = self.ok("register_source", path=str(notes))
        self.assertEqual((edited["source_id"], edited["changed"]), (first["source_id"], True))
        lines = self.s.read_jsonl("graph/sources.jsonl")
        self.assertEqual([line["id"] for line in lines], [first["source_id"]] * 2)
        self.assertEqual(set(lines[0]), {"id", "path", "sha256", "at"})
        other = Path(self.tmp.name) / "other.md"
        other.write_text("two\n")
        self.assertNotEqual(self.ok("register_source", path=str(other))["source_id"], first["source_id"])
        self.assertIn("must be absolute", self.bad("register_source", path="notes.md"))
        self.assertIn("is not a file", self.bad("register_source", path=self.tmp.name))

    def test_force_reimports_an_unchanged_file(self):
        notes = Path(self.tmp.name) / "notes.md"
        notes.write_text("one\n")
        first = self.ok("register_source", path=str(notes))
        self.assertFalse(self.ok("register_source", path=str(notes), force=False)["changed"])
        forced = self.ok("register_source", path=str(notes), force=True)
        self.assertEqual((forced["source_id"], forced["changed"]), (first["source_id"], True))
        lines = self.s.read_jsonl("graph/sources.jsonl")
        self.assertEqual([line["sha256"] for line in lines], [lines[0]["sha256"]] * 2)
        self.assertFalse(self.ok("register_source", path=str(notes))["changed"])
        self.assertIn("force must be true or false", self.bad("register_source", path=str(notes), force="yes"))

    def test_read_session(self):
        self.assertIn("pass goal_id, log_id", self.bad("read_session"))
        practice = self.ok("start_session", session_id=SID, mode="practice")["session"]["log"]
        out = self.ok("read_session", log_id=practice)
        self.assertEqual((out["goal"], out["log"], out["entries"][0]["type"]), (None, practice, "start"))
        self.assertIn("No log", self.bad("read_session", log_id="2026-01-01-zzzz"))
        gid = self.ok("start_session", session_id="s-2", goal_text="A goal")["goal"]["id"]
        (self.root / "goals" / gid / "sessions").rename(self.root / "goals" / gid / "old")
        self.assertEqual(self.ok("read_session", goal_id=gid), {"goal": gid, "log": None, "entries": []})

    def test_open_graph_page(self):
        gid = self.study()["goal"]["id"]
        page = self.root / "graph.html"
        calls = []

        def build(data, goal_id=None):
            calls.append((data, goal_id))
            page.write_text("<html></html>")
            return page

        with mock.patch.dict(sys.modules, {"graph_page": types.SimpleNamespace(build=build)}):
            self.assertEqual(self.ok("open_graph_page", goal_id=gid), {"path": str(page.resolve())})
            self.ok("open_graph_page")
            self.assertIn("No goal", self.bad("open_graph_page", goal_id="missing-abcd"))
        self.assertEqual(calls, [(self.s, gid), (self.s, None)])
        self.assertEqual(self.opened, [page.resolve(), page.resolve()])

        def newer(data, goal_id=None):
            raise store.FormatError("The data folder uses format 2. Update the plugin.")

        with mock.patch.dict(sys.modules, {"graph_page": types.SimpleNamespace(build=newer)}):
            self.assertIn("Update the plugin", self.bad("open_graph_page"))

    def test_open_in_browser(self):
        out = self.study()
        media = Path(out["paths"]["media"])
        picture = media / "balance.svg"
        picture.write_text("<svg/>")
        self.assertEqual(self.ok("open_in_browser", path=str(picture)), {"opened": str(picture.resolve())})
        self.assertEqual(self.opened, [picture.resolve()])
        outside = Path(self.tmp.name) / "outside.html"
        outside.write_text("<p>")
        self.assertIn("outside the data folder", self.bad("open_in_browser", path=str(outside)))
        link = media / "link.html"
        os.symlink(str(outside), str(link))
        self.assertIn("outside the data folder", self.bad("open_in_browser", path=str(link)))
        self.assertIn("outside the data folder", self.bad("open_in_browser", path=str(media / ".." / ".." / ".." / ".." / "outside.html")))
        self.assertIn("is not a file", self.bad("open_in_browser", path=str(media / "missing.svg")))
        self.assertIn("must be absolute", self.bad("open_in_browser", path="balance.svg"))
        self.assertEqual(len(self.opened), 1)

    def test_browser_failure(self):
        out = self.study()
        picture = Path(out["paths"]["media"]) / "a.svg"
        picture.write_text("<svg/>")
        with mock.patch.object(study_mcp, "open_browser", return_value=False):
            self.assertIn("No browser could be opened", self.bad("open_in_browser", path=str(picture)))


class StdioTest(unittest.TestCase):
    def test_over_stdio_with_isolated_python(self):
        with tempfile.TemporaryDirectory() as home:
            messages = [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                 "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                 "params": {"name": "start_session", "arguments": {"session_id": SID, "goal_text": "Ünïcode goal"}}},
            ]
            stdin = "".join(json.dumps(m) + "\n" for m in messages) + "not json\n"
            env = dict(os.environ, HOME=home)
            env.pop("CLAUDE_PLUGIN_OPTION_DATA_DIR", None)
            proc = subprocess.run(
                [sys.executable, "-I", str(SERVER / "study_mcp.py"), "--data-dir", "~/Study"],
                input=stdin.encode("utf-8"), capture_output=True, timeout=30, cwd=home, env=env,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr.decode())
            replies = [json.loads(line) for line in proc.stdout.decode("utf-8").splitlines()]
            self.assertEqual([r["id"] for r in replies], [1, 2, 3, None])
            self.assertEqual(replies[0]["result"]["protocolVersion"], "2025-06-18")
            self.assertEqual(len(replies[1]["result"]["tools"]), len(study_mcp.TOOLS))
            result = replies[2]["result"]
            self.assertFalse(result["isError"])
            goal = json.loads(result["content"][0]["text"])["goal"]
            self.assertEqual(goal["goal"], "Ünïcode goal")
            self.assertTrue((Path(home) / "Study" / "goals" / goal["id"] / "goal.json").is_file())
            self.assertEqual(replies[3]["error"]["code"], -32700)
            self.assertIn("unreadable message", (Path(home) / "Study" / "errors.log").read_text())


if __name__ == "__main__":
    unittest.main()
