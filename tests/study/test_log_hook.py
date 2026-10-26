import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "study"
SERVER = PLUGIN / "server"
HOOK = PLUGIN / "scripts" / "log_hook.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "hook"
sys.path.insert(0, str(SERVER))

import store  # noqa: E402

SESSION = "0d6c6a5e-1f2b-4c3d-9e8f-7a6b5c4d3e2f"
GOAL = "two-step-equations-k3f9"
LOG = "2026-10-25-a1b2"
CHECK = "In 2x + 3 = 11, which part do you undo first?"
CHECK_OPTIONS = ["the + 3", "the 2x", "the = 11", store.IDK]
CONFIDENCE_LABELS = ["Guessing", "Unsure", "Fairly sure", "Sure"]


def fixture(name):
    with open(FIXTURES / name, encoding="utf-8") as f:
        return json.load(f)


def asked(question, options, header="Check", multi=False):
    """One question as AskUserQuestion's input holds it."""
    return {
        "question": question, "header": header, "multiSelect": multi,
        "options": [{"label": o, "description": ""} for o in options],
    }


CONFIDENCE_Q = asked("How sure are you?", CONFIDENCE_LABELS, header="Confidence")


class HookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.data = self.home / "Study"
        self.s = store.Store(self.data)
        self.s.check_writable()

    def tearDown(self):
        self.tmp.cleanup()

    # Running the hook

    def run_hook(self, mode, payload=None, raw=None, extra=()):
        env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_")}
        env["CLAUDE_PLUGIN_OPTION_DATA_DIR"] = str(self.data)
        env["HOME"] = str(self.home)
        stdin = raw if raw is not None else json.dumps(payload)
        p = subprocess.run(
            [sys.executable, "-I", *extra, str(HOOK), mode], input=stdin.encode("utf-8"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=30,
        )
        self.assertEqual(p.returncode, 0, p.stderr.decode())
        return p

    def context(self, mode, payload, event):
        """Runs the hook and returns its additionalContext."""
        p = self.run_hook(mode, payload)
        self.assertTrue(p.stdout.strip(), "no output; stderr: " + p.stderr.decode())
        out = json.loads(p.stdout)["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], event)
        return out["additionalContext"]

    def silent(self, mode, payload=None, raw=None):
        p = self.run_hook(mode, payload, raw)
        self.assertEqual(p.stdout, b"")
        return p

    # Building a session

    def start(self, status="teaching", mode="study"):
        goal = None if mode == "practice" else GOAL
        if goal:
            self.s.write_goal({
                "id": GOAL, "title": "Two-step equations",
                "goal": "Solve ax + b = c for x and say why each step keeps the equation true",
                "status": status, "probe": None, "created": store.now(), "doneAt": None,
            })
            self.s.write_plan(GOAL, {"goal": GOAL, "version": 1, "steps": [
                {"id": "s1", "title": "Balance", "claim": "Same on both sides keeps it true", "dependsOn": []},
                {"id": "s2", "title": "Undo in reverse", "claim": "Undo the last operation first",
                 "dependsOn": ["s1"]},
            ]})
        self.s.write_marker(SESSION, {"mode": mode, "goal": goal, "log": LOG, "started": store.now()})
        self.s.append_log(goal, LOG, {"type": "start", "claudeSession": SESSION, "goal": goal})
        self.goal = goal

    def question(self, qid, text=CHECK, options=CHECK_OPTIONS, key=("the + 3",), kind="check", step="s2"):
        return self.s.append_log(self.goal, LOG, {
            "type": "question", "id": qid, "kind": kind, "step": None if kind == "probe" else step,
            "question": text, "options": list(options), "multi": len(key) > 1, "key": list(key),
            "explanation": "The + 3 was done to x last, so it comes off first.", "freeText": False,
        })

    def free_question(self, qid, text="Why do you subtract 3 first?"):
        return self.s.append_log(self.goal, LOG, {
            "type": "question", "id": qid, "kind": "check", "step": "s2", "question": text,
            "options": None, "multi": False, "key": ["Because + 3 was the last thing done to x"],
            "explanation": "Undo in reverse order.", "freeText": True,
        })

    def entries(self, after="question"):
        """The log's entries after the last entry of type `after`."""
        log = self.s.read_log(self.goal, LOG)
        last = max(i for i, e in enumerate(log) if e["type"] in (after, "start"))
        return [{k: v for k, v in e.items() if k not in ("n", "at")} for e in log[last + 1:]]

    def answer_input(self, questions, answers, annotations=None):
        payload = fixture("post_tool_use.json")
        tool_input = {"questions": questions, "answers": answers}
        if annotations is not None:
            tool_input["annotations"] = annotations
        payload["tool_input"] = tool_input
        payload["tool_response"] = dict(tool_input)
        return payload

    def errors_log(self):
        path = self.data / "errors.log"
        return path.read_text(encoding="utf-8") if path.exists() else ""


class NoMarkerTest(HookTest):
    def test_no_marker_is_silent_and_writes_nothing(self):
        self.goal = GOAL
        self.s.append_log(GOAL, LOG, {"type": "start", "claudeSession": SESSION, "goal": GOAL})
        self.question("q1")
        before = self.s.read_log(GOAL, LOG)
        for mode, name in (("answer", "post_tool_use.json"), ("prompt", "user_prompt_submit.json"),
                           ("compact", "session_start_compact.json")):
            with self.subTest(mode=mode):
                p = self.silent(mode, fixture(name))
                self.assertEqual(p.stderr, b"")
        self.assertEqual(self.s.read_log(GOAL, LOG), before)
        self.assertEqual(self.errors_log(), "")

    def test_missing_data_folder_is_silent(self):
        self.data = self.home / "nowhere"
        p = self.silent("prompt", fixture("user_prompt_submit.json"))
        self.assertEqual(p.stderr, b"")
        self.assertFalse(self.data.exists())

    def test_another_sessions_marker_is_ignored(self):
        self.start()
        self.free_question("q1")
        payload = dict(fixture("user_prompt_submit.json"), session_id="99999999-aaaa-bbbb-cccc-dddddddddddd")
        self.silent("prompt", payload)
        self.assertEqual(self.entries(), [])

    def test_unsafe_session_id_is_silent(self):
        self.start()
        self.silent("prompt", dict(fixture("user_prompt_submit.json"), session_id="../active/" + SESSION))
        self.assertEqual(self.errors_log(), "")

    def test_stale_marker_is_silent(self):
        self.start()
        self.free_question("q1")
        old = time.time() - store.MARKER_TTL - 3600
        marker = self.s.read_json(self.s.marker_rel(SESSION))
        marker["started"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(old))
        self.s.write_json(self.s.marker_rel(SESSION), marker)
        for rel in (self.s.marker_rel(SESSION), self.s.log_rel(GOAL, LOG)):
            os.utime(str(self.s.path(rel)), (old, old))
        self.silent("prompt", fixture("user_prompt_submit.json"))
        self.silent("compact", fixture("session_start_compact.json"))
        self.assertEqual(self.entries(), [])

    def imported(self, payload):
        p = self.run_hook("prompt", payload, extra=("-X", "importtime"))
        return {line.rsplit("|", 1)[-1].strip() for line in p.stderr.decode().splitlines()}

    def test_no_marker_anywhere_imports_nothing_heavy(self):
        imported = self.imported(fixture("user_prompt_submit.json"))
        self.assertIn("os", imported)  # the import list is really there
        for name in ("json", "re", "pathlib", "store"):
            self.assertNotIn(name, imported)

    def test_no_marker_for_this_session_does_not_import_store(self):
        self.s.write_marker("99999999-aaaa-bbbb-cccc-dddddddddddd",
                            {"mode": "practice", "goal": None, "log": LOG, "started": store.now()})
        imported = self.imported(fixture("user_prompt_submit.json"))
        self.assertIn("json", imported)
        self.assertNotIn("store", imported)
        self.assertNotIn("pathlib", imported)

    def test_garbage_with_no_marker_anywhere_is_silent(self):
        p = self.silent("answer", raw=(FIXTURES / "garbage.txt").read_text(encoding="utf-8"))
        self.assertEqual(p.stderr, b"")
        self.assertEqual(self.errors_log(), "")

    def test_no_marker_run_is_fast(self):
        payload = json.dumps(fixture("user_prompt_submit.json"))
        times = []
        for _ in range(5):
            started = time.perf_counter()
            self.run_hook("prompt", raw=payload)
            times.append(time.perf_counter() - started)
        self.assertLess(min(times), 0.1, times)

    def test_quick_data_dir_agrees_with_store(self):
        spec = importlib.util.spec_from_file_location("log_hook", str(HOOK))
        hook = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hook)
        saved = os.environ.get("CLAUDE_PLUGIN_OPTION_DATA_DIR")
        try:
            for value in (None, "", "  ", "${user_config.data_dir}", "~/Notes/Study", "/tmp/x/../Study", " /abs "):
                with self.subTest(value=value):
                    if value is None:
                        os.environ.pop("CLAUDE_PLUGIN_OPTION_DATA_DIR", None)
                    else:
                        os.environ["CLAUDE_PLUGIN_OPTION_DATA_DIR"] = value
                    self.assertEqual(
                        os.path.normpath(hook.quick_data_dir()), os.path.normpath(str(store.resolve_data_dir()))
                    )
        finally:
            if saved is None:
                os.environ.pop("CLAUDE_PLUGIN_OPTION_DATA_DIR", None)
            else:
                os.environ["CLAUDE_PLUGIN_OPTION_DATA_DIR"] = saved


class AnswerTest(HookTest):
    def setUp(self):
        super().setUp()
        self.start()

    def test_fixture_answer_is_matched_and_graded(self):
        self.question("q1")
        text = self.context("answer", fixture("post_tool_use.json"), "PostToolUse")
        self.assertEqual(text, 'q1: wrong (picked "the 2x"; key "the + 3"), confidence Sure')
        self.assertEqual(self.entries(), [
            {"type": "answer", "question": "q1", "picked": ["the 2x"], "other": None, "confidence": 95,
             "notes": "The 2 is stuck to the x, so it goes first", "freeText": None},
            {"type": "verdict", "question": "q1", "verdict": "wrong", "by": "code"},
        ])
        self.assertIsNone(store.open_question(self.s.read_log(GOAL, LOG)))

    def test_question_text_matches_with_whitespace_trimmed(self):
        self.question("q1", text="  " + CHECK + "\n")
        payload = self.answer_input([asked(CHECK, CHECK_OPTIONS), CONFIDENCE_Q],
                                    {CHECK: "the + 3", "How sure are you?": "Guessing"})
        self.assertEqual(self.context("answer", payload, "PostToolUse"),
                         'q1: right (picked "the + 3"; key "the + 3"), confidence Guessing')

    def test_confidence_header_mapping(self):
        for n, (label, value) in enumerate(store.CONFIDENCE.items(), start=1):
            with self.subTest(label=label):
                self.question(f"q{n}")
                payload = self.answer_input([asked(CHECK, CHECK_OPTIONS), CONFIDENCE_Q],
                                            {CHECK: "the + 3", "How sure are you?": label})
                text = self.context("answer", payload, "PostToolUse")
                self.assertTrue(text.endswith(f", confidence {label}"), text)
                self.assertEqual(self.entries()[0]["confidence"], value)

    def test_confidence_typed_as_other_is_not_given(self):
        self.question("q1")
        payload = self.answer_input([asked(CHECK, CHECK_OPTIONS), CONFIDENCE_Q],
                                    {CHECK: "the + 3", "How sure are you?": "kind of sure"})
        self.assertEqual(self.context("answer", payload, "PostToolUse"),
                         'q1: right (picked "the + 3"; key "the + 3"), confidence not given')
        self.assertIsNone(self.entries()[0]["confidence"])

    def test_no_confidence_on_a_probe(self):
        self.question("q1", kind="probe")
        payload = self.answer_input([asked(CHECK, CHECK_OPTIONS)], {CHECK: "the = 11"})
        self.assertEqual(self.context("answer", payload, "PostToolUse"),
                         'q1: wrong (picked "the = 11"; key "the + 3"), confidence not given')

    def test_predict_has_no_confidence_part(self):
        self.question("q1", kind="predict")
        payload = self.answer_input([asked(CHECK, CHECK_OPTIONS)], {CHECK: "the + 3"})
        self.assertEqual(self.context("answer", payload, "PostToolUse"), 'q1: right (picked "the + 3"; key "the + 3")')

    def test_i_dont_know(self):
        self.question("q1")
        payload = self.answer_input([asked(CHECK, CHECK_OPTIONS), CONFIDENCE_Q],
                                    {CHECK: store.IDK, "How sure are you?": "Unsure"})
        self.assertEqual(self.context("answer", payload, "PostToolUse"),
                         'q1: dontKnow (picked "I don\'t know"; key "the + 3"), confidence Unsure')
        self.assertEqual(self.entries()[1]["verdict"], "dontKnow")

    def test_multi_select(self):
        text = "Which of these keep 2x + 3 = 11 true?"
        options = ["subtract 3 from both sides", "divide only the left by 2", "divide both sides by 2", store.IDK]
        key = ("subtract 3 from both sides", "divide both sides by 2")
        cases = [
            ("subtract 3 from both sides, divide both sides by 2", "right"),
            ("subtract 3 from both sides, divide only the left by 2", "partly"),
            ("divide only the left by 2", "wrong"),
            ("divide both sides by 2, I don't know", "dontKnow"),
        ]
        for n, (answer, verdict) in enumerate(cases, start=1):
            with self.subTest(answer=answer):
                self.question(f"q{n}", text=text, options=options, key=key)
                payload = self.answer_input([asked(text, options, multi=True), CONFIDENCE_Q],
                                            {text: answer, "How sure are you?": "Sure"})
                message = self.context("answer", payload, "PostToolUse")
                picked = ", ".join(f'"{p}"' for p in answer.split(", "))
                self.assertEqual(message, f'q{n}: {verdict} (picked {picked}; key "subtract 3 from both sides", '
                                          f'"divide both sides by 2"), confidence Sure')
                self.assertEqual(self.entries()[0]["picked"], answer.split(", "))

    def test_label_holding_a_comma_is_one_pick(self):
        options = ["subtract 3, then divide by 2", "divide by 2, then subtract 3"]
        self.question("q1", options=options + [store.IDK], key=(options[0],))
        payload = self.answer_input([asked(CHECK, options + [store.IDK]), CONFIDENCE_Q],
                                    {CHECK: options[0], "How sure are you?": "Sure"})
        self.assertTrue(self.context("answer", payload, "PostToolUse").startswith("q1: right"))
        self.assertEqual(self.entries()[0]["picked"], [options[0]])

    def test_other_text_on_a_graded_question(self):
        self.question("q1")
        payload = self.answer_input([asked(CHECK, CHECK_OPTIONS), CONFIDENCE_Q],
                                    {CHECK: "the 3, since it was added last", "How sure are you?": "Fairly sure"})
        self.assertEqual(self.context("answer", payload, "PostToolUse"),
                         "q1: free-text answer via Other, grade it with record_verdict")
        self.assertEqual(self.entries(), [
            {"type": "answer", "question": "q1", "picked": [], "other": "the 3, since it was added last",
             "confidence": 70, "notes": None, "freeText": None},
        ])
        self.assertEqual([q["id"] for q in store.ungraded(self.s.read_log(GOAL, LOG))], ["q1"])

    def test_unmatched_answer_is_logged_as_ask(self):
        self.question("q1", text="Which side do you change first?")
        payload = self.answer_input([asked(CHECK, CHECK_OPTIONS), CONFIDENCE_Q],
                                    {CHECK: "the + 3", "How sure are you?": "Sure"})
        self.silent("answer", payload)
        self.assertEqual(self.entries(), [
            {"type": "ask", "question": CHECK, "header": "Check", "options": CHECK_OPTIONS,
             "picked": ["the + 3"], "other": None, "notes": None},
            {"type": "ask", "question": "How sure are you?", "header": "Confidence", "options": CONFIDENCE_LABELS,
             "picked": ["Sure"], "other": None, "notes": None},
        ])
        self.assertEqual(store.open_question(self.s.read_log(GOAL, LOG))["id"], "q1")

    def test_asks_beside_a_graded_question(self):
        self.question("q1")
        pace = asked("How fast should we go?", ["Slower", "Same", "Faster"], header="Pace")
        tools = asked("Which tools do you use?", ["Paper", "Calculator", "Graphing app"], header="Tools", multi=True)
        payload = self.answer_input(
            [pace, asked(CHECK, CHECK_OPTIONS), CONFIDENCE_Q, tools],
            {"How fast should we go?": "I would like more examples", CHECK: "the + 3", "How sure are you?": "Sure",
             "Which tools do you use?": "Paper, Calculator"},
            {"How fast should we go?": {"notes": "Step two lost me"}},
        )
        self.assertEqual(self.context("answer", payload, "PostToolUse"),
                         'q1: right (picked "the + 3"; key "the + 3"), confidence Sure')
        self.assertEqual(self.entries(after="start")[1:], [
            {"type": "ask", "question": "How fast should we go?", "header": "Pace",
             "options": ["Slower", "Same", "Faster"], "picked": [], "other": "I would like more examples",
             "notes": "Step two lost me"},
            {"type": "answer", "question": "q1", "picked": ["the + 3"], "other": None, "confidence": 95,
             "notes": None, "freeText": None},
            {"type": "verdict", "question": "q1", "verdict": "right", "by": "code"},
            {"type": "ask", "question": "Which tools do you use?", "header": "Tools",
             "options": ["Paper", "Calculator", "Graphing app"], "picked": ["Paper", "Calculator"], "other": None,
             "notes": None},
        ])

    def test_no_open_question_logs_ask(self):
        payload = self.answer_input([asked("Pick a goal size", ["Small", "Big"], header="Goal")],
                                    {"Pick a goal size": "Small"})
        self.silent("answer", payload)
        self.assertEqual([e["type"] for e in self.entries(after="start")], ["ask"])

    def test_answers_from_tool_response_json_text(self):
        self.question("q1")
        text = self.context("answer", fixture("post_tool_use_text_response.json"), "PostToolUse")
        self.assertEqual(text, 'q1: right (picked "the + 3"; key "the + 3"), confidence Fairly sure')
        self.assertEqual(self.entries()[0]["notes"], "Undo the last thing that was done to x")

    def test_answers_from_tool_response_dict(self):
        self.question("q1")
        payload = fixture("post_tool_use.json")
        del payload["tool_input"]["answers"]
        del payload["tool_input"]["annotations"]
        self.assertTrue(self.context("answer", payload, "PostToolUse").startswith('q1: wrong (picked "the 2x"'))

    def test_open_free_text_question_answered_through_ask_user_question(self):
        self.free_question("q1", text=CHECK)
        payload = self.answer_input([asked(CHECK, CHECK_OPTIONS)], {CHECK: "the + 3"})
        self.assertEqual(self.context("answer", payload, "PostToolUse"),
                         "q1: free-text answer via Other, grade it with record_verdict")
        self.assertEqual(self.entries()[0]["freeText"], "the + 3")
        self.assertEqual([e["type"] for e in self.entries()], ["answer"])

    def test_practice_log(self):
        self.goal = None
        self.s.write_marker(SESSION, {"mode": "practice", "goal": None, "log": LOG, "started": store.now()})
        self.question("q1", kind="probe")
        self.assertTrue(self.context("answer", fixture("post_tool_use.json"), "PostToolUse").startswith("q1: wrong"))
        self.assertEqual([e["type"] for e in self.entries()], ["answer", "verdict"])

    def test_unreadable_input_goes_to_errors_log(self):
        payload = fixture("post_tool_use.json")
        payload["tool_input"] = {"questions": "not a list"}
        payload["tool_response"] = "not json"
        p = self.silent("answer", payload)
        self.assertIn(b"could not read", p.stderr)
        self.assertIn('"questions": "not a list"', self.errors_log())
        self.assertEqual(self.entries(after="start"), [])


class PromptTest(HookTest):
    def setUp(self):
        super().setUp()
        self.start()

    def test_free_text_answer_is_linked(self):
        self.free_question("q1")
        prompt = fixture("user_prompt_submit.json")["prompt"]
        self.assertEqual(self.context("prompt", fixture("user_prompt_submit.json"), "UserPromptSubmit"),
                         "q1: free-text answer linked, grade it with record_verdict")
        self.assertEqual(self.entries(), [
            {"type": "learner", "text": prompt},
            {"type": "answer", "question": "q1", "picked": None, "other": None, "confidence": None, "notes": None,
             "freeText": prompt},
        ])
        self.assertEqual([q["id"] for q in store.ungraded(self.s.read_log(GOAL, LOG))], ["q1"])

    def test_only_the_first_message_is_linked(self):
        self.free_question("q1")
        self.context("prompt", fixture("user_prompt_submit.json"), "UserPromptSubmit")
        self.silent("prompt", dict(fixture("user_prompt_submit.json"), prompt="And another thought"))
        self.assertEqual([e["type"] for e in self.entries()], ["learner", "answer", "learner"])

    def test_no_open_question_logs_learner_only(self):
        self.silent("prompt", fixture("user_prompt_submit.json"))
        self.assertEqual([e["type"] for e in self.entries(after="start")], ["learner"])

    def test_open_multiple_choice_question_is_not_linked(self):
        self.question("q1")
        self.silent("prompt", fixture("user_prompt_submit.json"))
        self.assertEqual([e["type"] for e in self.entries()], ["learner"])

    def test_task_notification_is_ignored(self):
        self.free_question("q1")
        self.silent("prompt", fixture("task_notification.json"))
        self.silent("prompt", dict(fixture("task_notification.json"), prompt="<x-note id='1'>done</x-note>"))
        self.assertEqual(self.entries(), [])
        self.assertEqual(store.open_question(self.s.read_log(GOAL, LOG))["id"], "q1")

    def test_text_around_elements_is_the_learners(self):
        self.free_question("q1")
        for n, prompt in enumerate([
            "<b>subtract</b> first, then divide",
            "<pasted_content id=\"p1\">\nsubtract 3\n</pasted_content id=\"p1\">",
            "x < 5 and y > 2",
        ]):
            with self.subTest(prompt=prompt):
                p = self.run_hook("prompt", dict(fixture("user_prompt_submit.json"), prompt=prompt))
                learner = [e for e in self.entries() if e["type"] == "learner"]
                self.assertEqual(learner[-1]["text"], prompt)
                self.assertEqual(bool(p.stdout), n == 0)  # only the first one answers q1

    def test_slash_command_is_logged_not_linked(self):
        self.free_question("q1")
        self.silent("prompt", dict(fixture("user_prompt_submit.json"), prompt="/study stop"))
        self.assertEqual(self.entries(), [{"type": "learner", "text": "/study stop"}])
        self.context("prompt", dict(fixture("user_prompt_submit.json"), prompt="/3 of each side"), "UserPromptSubmit")
        self.assertEqual(self.entries()[-1]["freeText"], "/3 of each side")


class CompactTest(HookTest):
    def root(self, rel):
        return str(PLUGIN.resolve() / rel)

    def test_teaching(self):
        self.start()
        self.question("q1", step="s1")
        self.s.append_log(GOAL, LOG, {"type": "verdict", "question": "q1", "verdict": "right", "by": "code"})
        self.question("q2", text="Why subtract 3 first?", step="s2")
        self.assertEqual(
            self.context("compact", fixture("session_start_compact.json"), "SessionStart"),
            f'Study is on. Goal "Two-step equations" ({GOAL}), phase teaching, current step s2 "Undo in reverse", '
            f'open question q2 "Why subtract 3 first?". Reread {self.root("skills/study/teach.md")} and '
            f'{self.root("skills/study/questions.md")} before going on.',
        )

    def test_step_from_an_earlier_log(self):
        self.start()
        self.question("q1", step="s1")
        self.s.append_log(GOAL, LOG, {"type": "verdict", "question": "q1", "verdict": "right", "by": "code"})
        later = "2026-10-26-c3d4"
        self.s.write_marker(SESSION, {"mode": "study", "goal": GOAL, "log": later, "started": store.now()})
        self.s.append_log(GOAL, later, {"type": "start", "claudeSession": SESSION, "goal": GOAL})
        text = self.context("compact", fixture("session_start_compact.json"), "SessionStart")
        self.assertIn('phase teaching, current step s1 "Balance". Reread ', text)

    def test_probing(self):
        self.start(status="probing")
        self.question("q1", kind="probe")
        self.assertEqual(
            self.context("compact", fixture("session_start_compact.json"), "SessionStart"),
            f'Study is on. Goal "Two-step equations" ({GOAL}), phase probing, open question q1 "{CHECK}". '
            f'Reread {self.root("skills/study/probe.md")} and {self.root("skills/study/questions.md")} before going on.',
        )

    def test_planning(self):
        self.start(status="planning")
        self.assertEqual(
            self.context("compact", fixture("session_start_compact.json"), "SessionStart"),
            f'Study is on. Goal "Two-step equations" ({GOAL}), phase planning. '
            f'Reread {self.root("skills/study/plan.md")} before going on.',
        )

    def test_practice(self):
        self.start(mode="practice")
        self.assertEqual(
            self.context("compact", fixture("session_start_compact.json"), "SessionStart"),
            f"Study practice is on (log {LOG}). Reread {self.root('skills/practice/method.md')} before going on.",
        )
        self.s.append_log(None, LOG, {"type": "problem", "problem": "pr_x7k2"})
        self.s.append_log(None, LOG, {"type": "conclude", "problem": "pr_x7k2", "outcome": "solved",
                                      "verdict": "right"})
        self.s.append_log(None, LOG, {"type": "problem", "problem": "pr_q4r1"})
        self.assertEqual(
            self.context("compact", fixture("session_start_compact.json"), "SessionStart"),
            f"Study practice is on (log {LOG}), open problem pr_q4r1. "
            f"Reread {self.root('skills/practice/method.md')} before going on.",
        )


class BadInputTest(HookTest):
    def setUp(self):
        super().setUp()
        self.start()

    def test_garbage_stdin_exits_0_and_is_logged_raw(self):
        raw = (FIXTURES / "garbage.txt").read_text(encoding="utf-8")
        for mode in ("answer", "prompt", "compact"):
            with self.subTest(mode=mode):
                p = self.silent(mode, raw=raw)
                self.assertIn(b"could not parse", p.stderr)
        log = self.errors_log()
        self.assertEqual(log.count(raw), 3)
        self.assertIn("log_hook answer: could not parse the hook input", log)

    def test_binary_and_empty_stdin_exit_0(self):
        for raw in ("", "\x00\xff garbage", "[1, 2, 3]", "null"):
            with self.subTest(raw=raw):
                self.silent("prompt", raw=raw)

    def test_bad_mode_exits_0(self):
        p = self.silent("grade", fixture("user_prompt_submit.json"))
        self.assertIn(b"usage", p.stderr)

    def test_store_error_exits_0(self):
        self.free_question("q1")
        self.s.write_json("format.json", {"format": store.FORMAT + 1})
        p = self.silent("prompt", fixture("user_prompt_submit.json"))
        self.assertIn(b"FormatError", p.stderr)
        self.assertIn("FormatError", self.errors_log())


if __name__ == "__main__":
    unittest.main()
