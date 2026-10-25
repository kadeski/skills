"""Study's MCP server (spec section 9, contracts sections 3 to 5).

Run as `python3 -I study_mcp.py --data-dir <folder>`. It speaks MCP over stdio: one JSON-RPC 2.0
message per line. It implements the `initialize` handshake of protocol versions 2024-11-05 to
2025-11-25; a client that probes with `server/discover` first gets "method not found" and falls
back to `initialize`.

- Only protocol messages go to stdout. Errors go to stderr and <data>/errors.log.
- Every tool answers one text item holding JSON. A bad input answers `isError: true` with
  {"error": "<what to fix>"}, listing every problem found.
- All data reads and writes go through store.py. Standard library only; runs on Python 3.9.
"""
import argparse
import hashlib
import json
import os
import random
import re
import sys
import traceback
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import store  # noqa: E402

PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")  # newest first
STATEMENTS_CAP = 40
MATCHES_CAP = 50
CANDIDATES_CAP = 50
DUE_LIMIT = 50
STEP_KINDS = ("predict", "check")
OUTCOMES = ("solved", "solvedWithHints", "movedOn", "surrendered")
RUNGS = ("R0", "R1", "R2", "R3", "R4", "R5")
MISS_CLASSES = ("cue", "discrimination", "execution", "careless", "structural")
TEACHER_VERDICTS = tuple(v for v in store.VERDICTS if v != "skipped")
CONFIDENCES = sorted(store.CONFIDENCE.values())

_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_random = random.SystemRandom()


class ToolError(Exception):
    """A tool input the server refuses. `problems` lists every problem found."""

    def __init__(self, problems):
        self.problems = [problems] if isinstance(problems, str) else list(problems)
        super().__init__("; ".join(self.problems))


def open_browser(path):
    """Opens a file in the default browser. The only place the server does; tests replace it."""
    return webbrowser.open(Path(path).as_uri())


def _plugin_version():
    try:
        with open(Path(__file__).resolve().parents[1] / ".claude-plugin" / "plugin.json", encoding="utf-8") as f:
            return str(json.load(f)["version"])
    except (OSError, ValueError, KeyError, TypeError):
        return "0"


# Tool schemas (contracts section 3). Property order is the order the model writes them in.


def _text(description, **extra):
    return dict({"type": "string", "minLength": 1, "description": description}, **extra)


def _enum(values, description):
    return {"type": "string", "enum": list(values), "description": description}


_SESSION = _text("The Claude Code session id: the skill's ${CLAUDE_SESSION_ID}.")
_GOAL_ID = _text("A goal id, like two-step-equations-k3f9.")
_CONFIDENCE = {
    "type": "integer", "enum": CONFIDENCES,
    "description": "The learner's confidence: 10 Guessing, 40 Unsure, 70 Fairly sure, 95 Sure. Omit when not given.",
}

TOOLS = [
    ("start_session",
     "Start Study logging for this Claude session. Study with neither goal_text nor goal_id: lists "
     "unfinished goals, newest first, and writes nothing. Study with goal_id opens that goal; with "
     "goal_text creates one. Practice starts a practice log and returns the due list and candidate "
     "ideas. Opening or practice writes the active marker and a start entry.",
     {
         "session_id": _SESSION,
         "mode": _enum(("study", "practice"), "study (default) or practice."),
         "goal_text": _text("Study: the goal in the learner's words, to create a new goal."),
         "title": _text("Study, with goal_text: a short title. Defaults to the first words of goal_text."),
         "goal_id": _GOAL_ID,
         "topic": _text("Practice: limit candidates to ideas matching this, as graph_find matches."),
     }, ["session_id"]),
    ("end_session",
     "Stop logging for this Claude session: logs end and deletes the marker. Returns the ended log "
     "id, or null when nothing was being logged.",
     {"session_id": _SESSION}, ["session_id"]),
    ("list_goals",
     "Every goal with its status and last update, newest first.",
     {}, []),
    ("save_probe",
     "Save the probe result for the goal being studied. Refused while a question is open. Sets the "
     "status to planning and logs probe. goal and title replace the goal text and title with the "
     "concrete version the probe settled.",
     {
         "session_id": _SESSION,
         "goal_id": _GOAL_ID,
         "strands": {
             "type": "array", "minItems": 1,
             "description": "The separate things the goal depends on, each with where the learner's understanding ends.",
             "items": {
                 "type": "object",
                 "properties": {
                     "name": _text("The strand."),
                     "floor": {"type": "string", "description": "Something the learner reliably gets right."},
                     "ceiling": {"type": "string", "description": "Something they get wrong or don't know."},
                     "misconceptions": {"type": "array", "items": {"type": "string", "minLength": 1}},
                     "buildFrom": {"type": "string", "description": "What to build from."},
                 },
                 "required": ["name", "floor", "ceiling", "buildFrom"],
                 "additionalProperties": False,
             },
         },
         "summary": _text("One short paragraph on where the learner stands."),
         "goal": _text("The concrete goal text."),
         "title": _text("The concrete title."),
     }, ["session_id", "goal_id", "strands", "summary"]),
    ("save_plan",
     "Save the plan for the goal being studied: unique step ids, known dependencies, no cycles. "
     "Bumps the version and logs plan. Returns what read_plan returns.",
     {
         "session_id": _SESSION,
         "goal_id": _GOAL_ID,
         "steps": {
             "type": "array", "minItems": 1,
             "description": "The steps from what the learner holds to the goal, in teaching order.",
             "items": {
                 "type": "object",
                 "properties": {
                     "id": _text("A short id, like s1."),
                     "title": _text("A few words."),
                     "claim": _text("The one idea this step makes obvious."),
                     "dependsOn": {"type": "array", "items": {"type": "string", "minLength": 1},
                                   "description": "Ids of the steps it builds on."},
                 },
                 "required": ["id", "title", "claim", "dependsOn"],
                 "additionalProperties": False,
             },
         },
     }, ["session_id", "goal_id", "steps"]),
    ("read_plan",
     "The goal's plan, each step with its status: upcoming, current or visited. null with no plan.",
     {"goal_id": _GOAL_ID}, ["goal_id"]),
    ("finish_goal",
     "Mark the goal being studied done: sets status done and doneAt, logs end with the note and "
     "deletes the marker.",
     {"session_id": _SESSION, "goal_id": _GOAL_ID,
      "note": {"type": "string", "description": "How the goal ended, in a sentence."}},
     ["session_id", "goal_id", "note"]),
    ("pose_question",
     "Commit a graded question before asking it (probe, predict or check; ungraded questions never "
     "come here). Multiple choice: 2 to 4 options and a key of labels from them; the server adds "
     "\"I don't know\" when there is room, shuffles, and returns the options to ask in that order. "
     "Free text: free_text true, no options, and a key holding the model answer. Closes any open "
     "question of this session as skipped.",
     {
         "session_id": _SESSION,
         "kind": _enum(("probe", "predict", "check"), "probe (no step), predict or check (both need step_id)."),
         "step_id": _text("The plan step a predict or check is about. Leave out for probe."),
         "question": _text("The question as it will be asked."),
         "options": {"type": "array", "minItems": 2, "maxItems": 4, "items": {"type": "string", "minLength": 1},
                     "description": "Multiple choice: 2 to 4 distinct labels. Leave out for free text."},
         "explanation": _text("Why the right answer is right and the others are wrong. Write it before the key."),
         "key": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1},
                 "description": "Multiple choice: the right labels. Free text: one item, the model answer."},
         "multi": {"type": "boolean", "description": "True when the learner may pick several labels; needed when the key has several."},
         "free_text": {"type": "boolean", "description": "True for a question answered in chat."},
     }, ["session_id", "kind", "question", "explanation", "key"]),
    ("record_verdict",
     "Grade an answer: a free-text answer, or an \"Other\" answer to a multiple-choice question.",
     {
         "session_id": _SESSION,
         "question_id": _text("The question id, like q3."),
         "verdict": _enum(TEACHER_VERDICTS, "right, partly, wrong or dontKnow."),
         "note": {"type": "string", "description": "What was right or missing."},
         "confidence": _CONFIDENCE,
     }, ["session_id", "question_id", "verdict"]),
    ("record_answer",
     "Log a free-text answer the hook missed.",
     {
         "session_id": _SESSION,
         "question_id": _text("The question id, like q3."),
         "text": _text("The learner's answer as they wrote it."),
         "confidence": _CONFIDENCE,
     }, ["session_id", "question_id", "text"]),
    ("commit_problem",
     "Practice: commit a problem and its model solution before showing it. Refused while this "
     "session has an open problem.",
     {
         "session_id": _SESSION,
         "statement": _text("The problem as it will be shown. It never names its target."),
         "mode": _enum(("recall", "discrimination", "composition"), "recall, discrimination or composition."),
         "targets": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1},
                     "description": "The proposition or chain ids the problem practices."},
         "cue_class": _text("The kind of cue the statement gives."),
         "solution": _text("The model solution, revealed after conclude_problem."),
     }, ["session_id", "statement", "mode", "targets", "cue_class", "solution"]),
    ("conclude_problem",
     "Practice: conclude the open problem. Returns the committed solution to reveal and the "
     "targets' new due dates.",
     {
         "session_id": _SESSION,
         "problem_id": _text("The problem id, like pr_x7k2."),
         "outcome": _enum(OUTCOMES, "solved (no hint), solvedWithHints, movedOn or surrendered."),
         "verdict": _enum(TEACHER_VERDICTS, "right, partly, wrong or dontKnow."),
         "rung": {"type": ["string", "null"], "enum": list(RUNGS) + [None],
                  "description": "The highest hint rung given, R0 to R5, or null for no hint."},
         "miss_class": _enum(MISS_CLASSES, "For a miss: cue, discrimination, execution, careless or structural."),
         "retest": {"type": "boolean", "description": "True to retest the target soon in a new form."},
     }, ["session_id", "problem_id", "outcome", "verdict", "rung", "retest"]),
    ("due_list",
     "Practiced targets due now, longest overdue first. Targets never practiced are not due.",
     {"limit": {"type": "integer", "minimum": 1, "maximum": 200, "description": f"At most this many (default {DUE_LIMIT})."}},
     []),
    ("graph_overview",
     f"Graph counts, propositions per goal and up to {STATEMENTS_CAP} statements, the goal's first when goal_id is given.",
     {"goal_id": _GOAL_ID}, []),
    ("graph_find",
     f"Propositions whose statement or an alias matches, at most {MATCHES_CAP}. Case-insensitive. "
     "A pattern with no * matches anywhere in the text; with *, the whole text must match and * "
     "matches any run of characters, so *both sides* searches inside.",
     {"pattern": _text("Text to look for, with * as the only wildcard.")}, ["pattern"]),
    ("graph_chains",
     "Chains with their premise and conclusion statements: all, or those using node_id as a premise or conclusion.",
     {"node_id": _text("A proposition id, like p_x7k2.")}, []),
    ("graph_merge",
     "The only graph writer. Adds propositions and chains taught in one step or found in one source. "
     "A statement equal to an existing statement or alias (case and spacing ignored), or one with "
     "same_as, links to the existing proposition instead of adding one. A chain with the same "
     "premises and conclusion as an existing one is linked too.",
     {
         "origin": {
             "type": "object",
             "description": "{goal, log, step} for a taught step, or {source} for imported notes.",
             "properties": {"goal": _GOAL_ID, "log": _text("The session log id."),
                            "step": _text("The plan step id."), "source": _text("A source id, like src_a1b2.")},
             "additionalProperties": False,
         },
         "propositions": {
             "type": "array",
             "items": {
                 "type": "object",
                 "properties": {
                     "key": _text("A name local to this call, used by chains. Not p_ or c_."),
                     "statement": _text("One claim that stands alone, true outside the lesson."),
                     "same_as": _text("An existing proposition id this is the same idea as."),
                 },
                 "required": ["key", "statement"],
                 "additionalProperties": False,
             },
         },
         "chains": {
             "type": "array",
             "items": {
                 "type": "object",
                 "properties": {
                     "premises": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1},
                                  "description": "Local keys or existing p_ ids that together imply the conclusion."},
                     "conclusion": _text("A local key or an existing p_ id."),
                 },
                 "required": ["premises", "conclusion"],
                 "additionalProperties": False,
             },
         },
     }, ["origin", "propositions", "chains"]),
    ("register_source",
     "Register a notes file before extracting it. The same path keeps its source id; changed is "
     "true when the file is new or differs from its last import, or with force.",
     {"path": _text("The file's absolute path."),
      "force": {"type": "boolean", "description": "True to import it again even when unchanged."}}, ["path"]),
    ("read_session",
     "A session log's entries: the goal's newest log, or log_id. goal_id null with a log_id reads a practice log.",
     {"goal_id": _GOAL_ID, "log_id": _text("A log id, like 2026-10-25-a1b2.")}, []),
    ("open_graph_page",
     "Build the knowledge graph page and open it in the browser.",
     {"goal_id": _text("Show this goal first.")}, []),
    ("open_in_browser",
     "Open a file inside the data folder, such as a visual in a goal's media folder, in the browser.",
     {"path": _text("The file's absolute path, inside the data folder.")}, ["path"]),
]


def _schema(properties, required):
    out = {"type": "object", "properties": properties}
    if required:
        out["required"] = required
    out["additionalProperties"] = False
    return out


TOOL_LIST = [{"name": n, "description": d, "inputSchema": _schema(p, r)} for n, d, p, r in TOOLS]
SCHEMAS = {t["name"]: t["inputSchema"] for t in TOOL_LIST}


# Schema checks. Covers the keywords the schemas above use. An optional property set to null
# counts as left out.

_TYPE_NAMES = {"string": "a string", "integer": "an integer", "boolean": "true or false",
               "array": "a list", "object": "an object", "null": "null"}


def _is_type(name, value):
    if name == "null":
        return value is None
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "boolean":
        return isinstance(value, bool)
    return isinstance(value, {"string": str, "array": list, "object": dict}[name])


def _at(where, name):
    return f"{where}.{name}" if where else name


def schema_problems(schema, value, where, out):
    """Appends to `out` each way `value` breaks `schema`."""
    types = schema.get("type")
    if types is not None:
        names = types if isinstance(types, list) else [types]
        if not any(_is_type(n, value) for n in names):
            out.append(f"{where} must be {' or '.join(_TYPE_NAMES[n] for n in names)}")
            return
    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{where} must be one of {', '.join(json.dumps(v) for v in schema['enum'])}")
        return
    if isinstance(value, str) and len(value.strip()) < schema.get("minLength", 0):
        out.append(f"{where} must not be empty")
    if isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            out.append(f"{where} must be at least {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            out.append(f"{where} must be at most {schema['maximum']}")
    if isinstance(value, list):
        lo, hi = schema.get("minItems"), schema.get("maxItems")
        if (lo is not None and len(value) < lo) or (hi is not None and len(value) > hi):
            if hi is None:
                out.append(f"{where} must have at least {lo} item{'s' if lo > 1 else ''}")
            else:
                out.append(f"{where} must have {lo} to {hi} items")
        for i, item in enumerate(value):
            schema_problems(schema.get("items", {}), item, f"{where}[{i}]", out)
    if isinstance(value, dict) and "properties" in schema:
        props, required = schema["properties"], schema.get("required", [])
        for name in required:
            if name not in value:
                out.append(f"{_at(where, name)} is required")
        if schema.get("additionalProperties") is False:
            for name in value:
                if name not in props:
                    out.append(f"{_at(where, name)} is not a known property")
        for name, sub in props.items():
            if name in value and not (value[name] is None and name not in required):
                schema_problems(sub, value[name], _at(where, name), out)


# Small helpers


def _norm(text):
    """Text compared case and spacing ignored."""
    return " ".join(text.split()).casefold()


def _matcher(pattern):
    """graph_find's test: substring with no `*`, else a whole-text match where `*` is any run."""
    folded = pattern.strip().casefold()
    if "*" not in folded:
        return lambda text: folded in text.casefold()
    regex = re.compile("".join(".*" if part == "*" else re.escape(part) for part in re.split(r"(\*)", folded)), re.S)
    return lambda text: regex.fullmatch(text.casefold()) is not None


def _prop_matches(match, prop):
    return any(isinstance(t, str) and match(t) for t in [prop.get("statement")] + prop.get("aliases", []))


def _title_from(text):
    """The first words of a goal text, as its default title."""
    title = " ".join(text.split()[:6])[:60].rstrip(" .,;:!?")
    return title or text.strip()[:60]


def _time(dt):
    return dt.strftime(_TIME_FORMAT)


def _goal_ids(prop):
    return {s.get("goal") for s in prop.get("sources", []) if isinstance(s, dict) and s.get("goal")}


def _find_cycle(deps):
    """One dependency loop as [a, b, ..., a], or None. `deps` maps step id -> ids it depends on."""
    state, stack = {}, []

    def visit(node):
        state[node] = "open"
        stack.append(node)
        for dep in deps.get(node, []):
            if state.get(dep) == "open":
                return stack[stack.index(dep):] + [dep]
            if dep not in state:
                found = visit(dep)
                if found:
                    return found
        stack.pop()
        state[node] = "done"
        return None

    for node in deps:
        if node not in state:
            found = visit(node)
            if found:
                return found
    return None


def gap_days(conclude, previous):
    """Days until a target is due again after `conclude` (spec section 8, Due list).

    `previous` is the gap the target's previous conclude set, or None. A clean solve doubles it.
    """
    outcome, rung = conclude.get("outcome"), conclude.get("rung")
    if outcome in ("movedOn", "surrendered") or rung in ("R3", "R4", "R5") or conclude.get("retest"):
        return 1
    if outcome == "solvedWithHints" or rung in ("R0", "R1", "R2"):
        return 3
    if outcome == "solved":
        return min(60, max(3, 2 * (previous or 0)))
    return 1


def due_state(data):
    """target id -> {"due": datetime, "gap": days, "outcome": latest outcome}, from problems.jsonl."""
    lines = data.read_jsonl("practice/problems.jsonl")
    commits = {line.get("id"): line for line in lines if line.get("type") == "commit"}
    state = {}
    for line in lines:
        commit = commits.get(line.get("id"))
        if line.get("type") != "conclude" or commit is None:
            continue
        try:
            at = store.parse_time(line["at"])
        except (KeyError, TypeError, ValueError):
            continue
        for target in commit.get("targets") or []:
            gap = gap_days(line, state.get(target, {}).get("gap"))
            state[target] = {"due": at + timedelta(days=gap), "gap": gap, "outcome": line.get("outcome")}
    return state


# The server


class Server:
    def __init__(self, data):
        self.store = data
        self.version = _plugin_version()

    # Protocol

    def handle_line(self, line):
        """The response to one line of stdin, or None."""
        try:
            message = json.loads(line.decode("utf-8") if isinstance(line, bytes) else line)
        except ValueError as e:
            self.log_error(f"unreadable message ({e}): {line[:200]!r}")
            return _rpc_error(None, -32700, "Parse error: send one JSON-RPC message per line")
        return self.handle(message)

    def handle(self, message):
        """The response to one JSON-RPC message, or None for a notification or a response."""
        if not isinstance(message, dict):
            return _rpc_error(None, -32600, "Invalid Request: send one JSON object per line")
        msg_id = message.get("id")
        method = message.get("method")
        if not isinstance(method, str):
            if "result" in message or "error" in message:
                return None
            return _rpc_error(msg_id, -32600, "Invalid Request: method is missing")
        if "id" not in message:
            return None  # notifications/initialized, notifications/cancelled and any other
        params = message.get("params")
        if params is None:
            params = {}
        if not isinstance(params, dict):
            return _rpc_error(msg_id, -32602, "params must be an object")
        try:
            if method == "initialize":
                result = self.initialize(params)
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": TOOL_LIST}
            elif method == "tools/call":
                name, args = params.get("name"), params.get("arguments")
                if name not in SCHEMAS:
                    return _rpc_error(msg_id, -32602, f"Unknown tool: {name}")
                if args is None:
                    args = {}
                if not isinstance(args, dict):
                    return _rpc_error(msg_id, -32602, "arguments must be an object")
                result = self.call_tool(name, args)
            else:
                return _rpc_error(msg_id, -32601, f"Method not found: {method}")
        except Exception as e:  # a bug: keep serving
            self.log_error(f"{method} failed:\n{traceback.format_exc()}")
            return _rpc_error(msg_id, -32603, f"Internal error: {e}")
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    def initialize(self, params):
        requested = params.get("protocolVersion")
        version = requested if requested in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
        return {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "study", "version": self.version},
        }

    def call_tool(self, name, args):
        """A tools/call result: one text item holding JSON, with isError on a refused input."""
        try:
            problems = []
            schema_problems(SCHEMAS[name], args, "", problems)
            if problems:
                raise ToolError(problems)
            required = SCHEMAS[name].get("required", [])
            args = {k: v for k, v in args.items() if v is not None or k in required}
            value, is_error = getattr(self, "tool_" + name)(**args), False
        except ToolError as e:
            value, is_error = {"error": str(e)}, True
        except store.StoreError as e:  # FormatError too: its message says to update the plugin
            value, is_error = {"error": str(e)}, True
        except Exception as e:  # a bug: say so and keep serving
            self.log_error(f"{name} failed:\n{traceback.format_exc()}")
            value = {"error": f"The Study server failed in {name}: {e}. Details are in {self.store.path('errors.log')}."}
            is_error = True
        return {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}], "isError": is_error}

    def log_error(self, text):
        """Writes to stderr and appends to <data>/errors.log. Never raises."""
        try:
            sys.stderr.write(f"study_mcp: {text}\n")
            sys.stderr.flush()
        except (OSError, ValueError):
            pass
        try:
            self.store.root.mkdir(parents=True, exist_ok=True)
            with open(self.store.path("errors.log"), "a", encoding="utf-8") as f:
                f.write(f"{store.now()} study_mcp: {text}\n")
        except OSError:
            pass

    # Shared checks

    def _goal(self, goal_id):
        goal = self.store.read_goal(goal_id)
        if not isinstance(goal, dict):
            raise ToolError(f"No goal {goal_id!r}: list_goals shows the goal ids")
        return goal

    def _marker(self, session_id, mode=None, tool=""):
        """The live marker of `session_id`, refusing when there is none or it is the other mode."""
        marker = self.store.read_marker(session_id)
        if marker is None:
            raise ToolError(f"Study is not logging session {session_id}: call start_session first")
        if mode == "study" and marker.get("mode") != "study":
            raise ToolError(f"{tool} works in study sessions; this session is practice")
        if mode == "practice" and marker.get("mode") != "practice":
            raise ToolError(f"{tool} works in practice sessions: call start_session with mode \"practice\"")
        return marker

    def _studying(self, session_id, goal_id, tool):
        """(marker, goal) for a study tool on the goal this session is studying."""
        marker = self._marker(session_id, "study", tool)
        if goal_id != marker.get("goal"):
            raise ToolError(f"This session is studying {marker.get('goal')!r}, not {goal_id!r}")
        return marker, self._goal(goal_id)

    def _entries(self, marker):
        return self.store.read_log(marker.get("goal"), marker["log"])

    def _question(self, marker, question_id):
        for e in self._entries(marker):
            if e.get("type") == "question" and e.get("id") == question_id:
                return e
        raise ToolError(f"No question {question_id!r} in this session's log")

    # Sessions

    def tool_start_session(self, session_id, mode="study", goal_text=None, title=None, goal_id=None, topic=None):
        store.check_id(session_id, "session_id")
        problems = []
        if mode == "practice":
            for name, value in (("goal_text", goal_text), ("title", title), ("goal_id", goal_id)):
                if value is not None:
                    problems.append(f"{name} is for study sessions; leave it out for practice")
        else:
            if topic is not None:
                problems.append("topic is for practice sessions; leave it out for study")
            if goal_text is not None and goal_id is not None:
                problems.append("pass goal_id to open a goal or goal_text to create one, not both")
            elif title is not None and goal_text is None:
                problems.append("title only goes with goal_text, when creating a goal")
            if goal_id is not None and not isinstance(self.store.read_goal(goal_id), dict):
                problems.append(f"No goal {goal_id!r}: call start_session with no goal to list them")
        if problems:
            raise ToolError(problems)
        if mode == "practice":
            return self._start_practice(session_id, topic)
        if goal_text is None and goal_id is None:
            fields = ("id", "title", "goal", "status", "updated")
            return {"goals": [{k: g.get(k) for k in fields} for g in self.store.list_goals() if g.get("status") != "done"]}
        if goal_id is None:
            created = store.now()
            title = (title or _title_from(goal_text)).strip()
            goal = self.store.write_goal({
                "id": self.store.new_goal_id(title),
                "title": title,
                "goal": goal_text.strip(),
                "status": "probing",
                "probe": None,
                "created": created,
                "updated": created,
                "doneAt": None,
            })
        else:
            goal = self._goal(goal_id)
        earlier = self.store.log_ids(goal["id"])
        last_sitting = self.store.read_log(goal["id"], earlier[-1]) if earlier else []
        log_id = self._begin(session_id, "study", goal["id"])
        folder = self.store.path(self.store.goal_rel(goal["id"]))
        (folder / "media").mkdir(parents=True, exist_ok=True)
        return {
            "session": {"log": log_id, "mode": "study"},
            "goal": goal,
            "plan": self.tool_read_plan(goal["id"])["plan"],
            "lastSitting": last_sitting,
            "graph": self.tool_graph_overview(goal["id"]),
            "paths": {"goal": str(folder.absolute()), "media": str((folder / "media").absolute())},
        }

    def _start_practice(self, session_id, topic):
        log_id = self._begin(session_id, "practice", None)
        media = self.store.path("practice", "media")
        media.mkdir(parents=True, exist_ok=True)
        props, chains = self.store.graph()
        if topic is None:
            matched = list(props)
        else:
            match = _matcher(topic)
            matched = [pid for pid, p in props.items() if _prop_matches(match, p)]
        picked = set(matched)
        chain_ids = [cid for cid, c in chains.items()
                     if topic is None or c.get("conclusion") in picked or any(p in picked for p in c.get("premises", []))]
        return {
            "session": {"log": log_id, "mode": "practice"},
            "due": self.tool_due_list()["due"],
            "candidates": {
                "propositions": [{"id": pid, "statement": props[pid]["statement"]} for pid in matched[:CANDIDATES_CAP]],
                "chains": [_chain_view(chains[cid], props) for cid in chain_ids[:CANDIDATES_CAP]],
            },
            "paths": {"media": str(media.absolute())},
        }

    def _begin(self, session_id, mode, goal_id):
        """Starts a new log with a start entry and points the session's marker at it."""
        log_id = self.store.new_log_id(goal_id)
        self.store.append_log(goal_id, log_id, {"type": "start", "claudeSession": session_id, "goal": goal_id})
        self.store.write_marker(session_id, {"mode": mode, "goal": goal_id, "log": log_id, "started": store.now()})
        return log_id

    def tool_end_session(self, session_id):
        store.check_id(session_id, "session_id")
        marker = self.store.read_marker(session_id)
        if marker is None:
            self.store.delete_marker(session_id)  # a stale one, if any
            return {"ended": None}
        self.store.append_log(marker.get("goal"), marker["log"], {"type": "end"})
        self.store.delete_marker(session_id)
        return {"ended": marker["log"]}

    # Goals and plans

    def tool_list_goals(self):
        fields = ("id", "title", "goal", "status", "updated", "doneAt")
        return {"goals": [{k: g.get(k) for k in fields} for g in self.store.list_goals()]}

    def tool_save_probe(self, session_id, goal_id, strands, summary, goal=None, title=None):
        marker, record = self._studying(session_id, goal_id, "save_probe")
        open_q = store.open_question(self._entries(marker))
        if open_q:
            raise ToolError(f"Question {open_q.get('id')} is still open: wait for the learner's answer before save_probe")
        record["probe"] = {
            "strands": [
                {"name": s["name"].strip(), "floor": s["floor"], "ceiling": s["ceiling"],
                 "misconceptions": list(s.get("misconceptions") or []), "buildFrom": s["buildFrom"]}
                for s in strands
            ],
            "summary": summary,
        }
        if goal is not None:
            record["goal"] = goal.strip()
        if title is not None:
            record["title"] = title.strip()
        record["status"] = "planning"
        record["doneAt"] = None
        self.store.write_goal(record)
        self.store.append_log(goal_id, marker["log"], {"type": "probe"})
        return {"goal": record}

    def tool_save_plan(self, session_id, goal_id, steps):
        marker, _ = self._studying(session_id, goal_id, "save_plan")
        problems, ids, deps = [], [], {}
        for s in steps:
            if s["id"] in ids:
                problems.append(f"step id {s['id']!r} is used twice")
            ids.append(s["id"])
        for s in steps:
            for dep in s["dependsOn"]:
                if dep == s["id"]:
                    problems.append(f"step {s['id']!r} depends on itself")
                elif dep not in ids:
                    problems.append(f"step {s['id']!r} depends on {dep!r}, which is not a step")
                else:
                    deps.setdefault(s["id"], []).append(dep)
        cycle = _find_cycle(deps)
        if cycle:
            problems.append("the dependencies form a loop: " + " -> ".join(cycle))
        if problems:
            raise ToolError(problems)
        old = self.store.read_plan(goal_id)
        version = old.get("version") if isinstance(old, dict) else None
        version = (version if isinstance(version, int) else 0) + 1
        self.store.write_plan(goal_id, {
            "goal": goal_id,
            "version": version,
            "steps": [{"id": s["id"], "title": s["title"], "claim": s["claim"], "dependsOn": list(s["dependsOn"])}
                      for s in steps],
        })
        self.store.append_log(goal_id, marker["log"], {"type": "plan", "version": version})
        return self.tool_read_plan(goal_id)

    def tool_read_plan(self, goal_id):
        self._goal(goal_id)
        plan = self.store.read_plan(goal_id)
        if not isinstance(plan, dict):
            return {"plan": None}
        statuses = store.step_statuses(plan, self.store.goal_entries(goal_id))
        steps = [dict(s, status=statuses.get(s.get("id"), "upcoming")) for s in plan.get("steps", [])]
        return {"plan": {"goal": plan.get("goal", goal_id), "version": plan.get("version"), "steps": steps}}

    def tool_finish_goal(self, session_id, goal_id, note):
        marker, goal = self._studying(session_id, goal_id, "finish_goal")
        self.store.append_log(goal_id, marker["log"], {"type": "end", "note": note})
        goal["status"] = "done"
        goal["doneAt"] = store.now()
        self.store.write_goal(goal)
        self.store.delete_marker(session_id)
        return {"goal": goal}

    # Questions (spec section 5)

    def tool_pose_question(self, session_id, kind, question, explanation, key,
                           step_id=None, options=None, multi=False, free_text=False):
        marker = self._marker(session_id, "study", "pose_question")
        goal_id = marker["goal"]
        problems = []
        if kind not in STEP_KINDS:
            if step_id is not None:
                problems.append("a probe question has no step: leave step_id out")
        elif step_id is None:
            problems.append(f"a {kind} question needs step_id, the plan step it is about")
        else:
            plan = self.store.read_plan(goal_id)
            steps = [s.get("id") for s in plan.get("steps", [])] if isinstance(plan, dict) else []
            if not steps:
                problems.append(f"step_id {step_id!r} needs a plan: call save_plan first")
            elif step_id not in steps:
                problems.append(f"step_id {step_id!r} is not a plan step; the steps are {', '.join(steps)}")
        key = [k.strip() for k in key]
        if len(set(key)) != len(key):
            problems.append("key lists a label twice")
        labels = None
        if free_text:
            if options is not None:
                problems.append("a free-text question has no options: leave options out")
            if multi:
                problems.append("a free-text question can't be multi: leave multi out")
            if len(key) != 1:
                problems.append("a free-text question's key is a one-item list holding the model answer")
        elif options is None:
            problems.append("a multiple-choice question needs 2 to 4 options; for free text set free_text true")
        else:
            labels = [o.strip() for o in options]
            seen = set()
            for label in labels:
                if label.casefold() == store.IDK.casefold():
                    problems.append(f"leave {store.IDK!r} out of options: the server adds it")
                elif label.casefold() in seen:
                    problems.append(f"option {label!r} is listed twice")
                seen.add(label.casefold())
            for k in key:
                if k not in labels:
                    problems.append(f"key {k!r} is not one of the options")
            if len(key) > 1 and not multi:
                problems.append("the key has several labels, so set multi true")
        if problems:
            raise ToolError(problems)
        if labels is not None:
            if len(labels) <= 3:
                labels.append(store.IDK)
            _random.shuffle(labels)
        entries = self._entries(marker)
        result = {}
        closed = store.open_question(entries)
        if closed:
            self.store.append_log(goal_id, marker["log"],
                                  {"type": "verdict", "question": closed.get("id"), "verdict": "skipped", "by": "server"})
            result["closed"] = closed.get("id")
        numbers = [int(e["id"][1:]) for e in entries
                   if e.get("type") == "question" and re.fullmatch(r"q[0-9]+", str(e.get("id")))]
        question_id = f"q{max(numbers, default=0) + 1}"
        self.store.append_log(goal_id, marker["log"], {
            "type": "question",
            "id": question_id,
            "kind": kind,
            "step": step_id,
            "question": question.strip(),
            "options": labels,
            "multi": bool(multi),
            "key": key,
            "explanation": explanation,
            "freeText": bool(free_text),
        })
        if step_id is not None:
            goal = self._goal(goal_id)
            if goal.get("status") in ("probing", "planning"):
                goal["status"] = "teaching"
                self.store.write_goal(goal)
        out = {"question_id": question_id}
        if labels is not None:
            out["options"] = labels
        out.update(result)
        return out

    def tool_record_verdict(self, session_id, question_id, verdict, note=None, confidence=None):
        marker = self._marker(session_id)
        self._question(marker, question_id)
        self.store.append_log(marker.get("goal"), marker["log"], {
            "type": "verdict", "question": question_id, "verdict": verdict, "by": "teacher",
            "note": note, "confidence": confidence,
        })
        return {"question_id": question_id, "verdict": verdict}

    def tool_record_answer(self, session_id, question_id, text, confidence=None):
        marker = self._marker(session_id)
        self._question(marker, question_id)
        self.store.append_log(marker.get("goal"), marker["log"], {
            "type": "answer", "question": question_id, "picked": None, "other": None,
            "confidence": confidence, "notes": None, "freeText": text,
        })
        return {"question_id": question_id}

    # Practice (spec sections 2 and 8)

    def tool_commit_problem(self, session_id, statement, mode, targets, cue_class, solution):
        marker = self._marker(session_id, "practice", "commit_problem")
        props, chains = self.store.graph()
        problems = []
        for t in targets:
            if t not in props and t not in chains:
                problems.append(f"target {t!r} is not a proposition or chain id")
        if len(set(targets)) != len(targets):
            problems.append("targets lists an id twice")
        lines = self.store.read_jsonl("practice/problems.jsonl")
        concluded = {line.get("id") for line in lines if line.get("type") == "conclude"}
        for line in lines:
            if line.get("type") == "commit" and line.get("log") == marker["log"] and line.get("id") not in concluded:
                problems.append(f"problem {line.get('id')} is still open: conclude_problem first")
        if problems:
            raise ToolError(problems)
        problem_id = store.new_id("pr_", taken={line.get("id") for line in lines})
        self.store.append_jsonl("practice/problems.jsonl", {
            "type": "commit", "id": problem_id, "at": store.now(), "log": marker["log"], "statement": statement,
            "mode": mode, "targets": list(targets), "cueClass": cue_class, "solution": solution,
        })
        self.store.append_log(None, marker["log"], {"type": "problem", "problem": problem_id})
        return {"problem_id": problem_id}

    def tool_conclude_problem(self, session_id, problem_id, outcome, verdict, rung, retest, miss_class=None):
        marker = self._marker(session_id, "practice", "conclude_problem")
        lines = self.store.read_jsonl("practice/problems.jsonl")
        commit = next((line for line in lines if line.get("type") == "commit" and line.get("id") == problem_id), None)
        problems = []
        if commit is None:
            problems.append(f"No problem {problem_id!r}: commit_problem returns the id")
        elif commit.get("log") != marker["log"]:
            problems.append(f"problem {problem_id} belongs to log {commit.get('log')}, not this session's")
        elif any(line.get("type") == "conclude" and line.get("id") == problem_id for line in lines):
            problems.append(f"problem {problem_id} is already concluded")
        if outcome == "solved" and rung is not None:
            problems.append("solved means no hint: use solvedWithHints when a rung was given")
        if outcome == "solvedWithHints" and rung is None:
            problems.append("solvedWithHints needs rung, the highest hint rung given")
        if problems:
            raise ToolError(problems)
        self.store.append_jsonl("practice/problems.jsonl", {
            "type": "conclude", "id": problem_id, "at": store.now(), "outcome": outcome, "verdict": verdict,
            "rung": rung, "missClass": miss_class, "retest": retest,
        })
        self.store.append_log(None, marker["log"],
                              {"type": "conclude", "problem": problem_id, "outcome": outcome, "verdict": verdict})
        state = due_state(self.store)
        due = [{"target": t, "due": _time(state[t]["due"])} for t in commit.get("targets") or [] if t in state]
        return {"problem_id": problem_id, "solution": commit.get("solution"), "due": due}

    def tool_due_list(self, limit=DUE_LIMIT):
        props, chains = self.store.graph()
        now = datetime.now(timezone.utc)
        rows = []
        for target, s in due_state(self.store).items():
            statement = _statement(target, props, chains)
            if s["due"] <= now and statement is not None:
                rows.append((s["due"], target, statement, s["outcome"]))
        rows.sort(key=lambda r: (r[0], r[1]))
        return {"due": [{"target": t, "statement": st, "due": _time(d), "lastOutcome": o}
                        for d, t, st, o in rows[:limit]]}

    # Graph (spec section 8, contracts section 5)

    def tool_graph_overview(self, goal_id=None):
        if goal_id is not None:
            self._goal(goal_id)
        props, chains = self.store.graph()
        by_goal = {}
        for p in props.values():
            for g in sorted(_goal_ids(p)):
                by_goal[g] = by_goal.get(g, 0) + 1
        first = [p for p in props.values() if goal_id in _goal_ids(p)] if goal_id else []
        rest = [p for p in props.values() if not goal_id or goal_id not in _goal_ids(p)]
        return {
            "propositions": len(props),
            "chains": len(chains),
            "byGoal": by_goal,
            "statements": [{"id": p["id"], "statement": p.get("statement")} for p in (first + rest)[:STATEMENTS_CAP]],
        }

    def tool_graph_find(self, pattern):
        props, _ = self.store.graph()
        match = _matcher(pattern)
        found = [p for p in props.values() if _prop_matches(match, p)]
        return {"matches": [{"id": p["id"], "statement": p.get("statement"), "aliases": p.get("aliases", [])}
                            for p in found[:MATCHES_CAP]]}

    def tool_graph_chains(self, node_id=None):
        props, chains = self.store.graph()
        if node_id is not None and node_id not in props:
            raise ToolError(f"{node_id!r} is not a proposition id: graph_find finds them")
        return {"chains": [_chain_view(c, props) for c in chains.values()
                           if node_id is None or node_id == c.get("conclusion") or node_id in c.get("premises", [])]}

    def tool_graph_merge(self, origin, propositions, chains):
        problems = []
        source = self._origin(origin, problems)
        props, old_chains = self.store.graph()
        texts = {pid: {_norm(t) for t in [p.get("statement")] + p.get("aliases", []) if isinstance(t, str)}
                 for pid, p in props.items()}
        by_text = {}
        for pid, known in texts.items():
            for t in known:
                by_text.setdefault(t, pid)
        ids, bad_keys = {}, set()
        new_props, aliases, linked = [], [], []
        for i, item in enumerate(propositions):
            where, key = f"propositions[{i}]", item["key"]
            statement, same = " ".join(item["statement"].split()), item.get("same_as")
            if key in ids or key in bad_keys:
                problems.append(f"{where}.key {key!r} is used twice")
                continue
            if key.startswith(("p_", "c_")):
                problems.append(f"{where}.key {key!r} starts like an id: pick a plain key such as a, b")
                bad_keys.add(key)
                continue
            if same is not None and same not in props:
                problems.append(f"{where}.same_as {same!r} is not a proposition id")
                bad_keys.add(key)
                continue
            target = same if same is not None else by_text.get(_norm(statement))
            if target is None:
                target = store.new_id("p_", taken=set(props) | {pid for pid, _ in new_props})
                new_props.append((target, statement))
                by_text[_norm(statement)] = target
            elif target in props:
                if _norm(statement) not in texts[target]:
                    aliases.append((target, statement))
                    texts[target].add(_norm(statement))
                    by_text.setdefault(_norm(statement), target)
                if target not in linked:
                    linked.append(target)
            ids[key] = target
        chain_sigs = {}
        for cid, c in old_chains.items():
            chain_sigs.setdefault((frozenset(c.get("premises", [])), c.get("conclusion")), cid)
        new_chains, linked_chains, touched_chains = [], [], []
        for i, item in enumerate(chains):
            ends = [(f"chains[{i}].premises[{j}]", e) for j, e in enumerate(item["premises"])]
            ends.append((f"chains[{i}].conclusion", item["conclusion"]))
            resolved = []
            for where, end in ends:
                if end in ids:
                    resolved.append(ids[end])
                elif end in props:
                    resolved.append(end)
                elif end in bad_keys:
                    resolved.append(None)
                else:
                    problems.append(f"{where} {end!r} is neither a key in propositions nor a proposition id")
                    resolved.append(None)
            if None in resolved:
                continue
            premises, conclusion = resolved[:-1], resolved[-1]
            if conclusion in premises:
                problems.append(f"chains[{i}]: the conclusion is also a premise")
                continue
            if len(set(premises)) != len(premises):
                problems.append(f"chains[{i}]: a premise is listed twice")
                continue
            sig = (frozenset(premises), conclusion)
            cid = chain_sigs.get(sig)
            if cid is None:
                cid = store.new_id("c_", taken=set(old_chains) | {c for c, _, _ in new_chains})
                new_chains.append((cid, premises, conclusion))
                chain_sigs[sig] = cid
            elif cid in old_chains and cid not in linked_chains:
                linked_chains.append(cid)
            if cid not in touched_chains:
                touched_chains.append(cid)
        if problems:
            raise ToolError(problems)
        for pid, statement in new_props:
            self.store.append_jsonl("graph/propositions.jsonl",
                                    {"op": "add", "id": pid, "statement": statement, "sources": [source]})
        for pid, text in aliases:
            self.store.append_jsonl("graph/propositions.jsonl", {"op": "alias", "id": pid, "text": text})
        for pid in linked:
            if source not in props[pid]["sources"]:
                self.store.append_jsonl("graph/propositions.jsonl", {"op": "source", "id": pid, "source": source})
        for cid, premises, conclusion in new_chains:
            self.store.append_jsonl("graph/chains.jsonl", {"op": "add", "id": cid, "premises": premises,
                                                           "conclusion": conclusion, "sources": [source]})
        for cid in linked_chains:
            if source not in old_chains[cid]["sources"]:
                self.store.append_jsonl("graph/chains.jsonl", {"op": "source", "id": cid, "source": source})
        if "step" in source:
            touched = []
            for pid in ids.values():
                if pid not in touched:
                    touched.append(pid)
            self.store.append_log(source["goal"], source["log"], {
                "type": "extracted", "step": source["step"], "propositions": touched, "chains": touched_chains,
            })
        return {
            "ids": ids,
            "added": {"propositions": len(new_props), "chains": len(new_chains)},
            "linked": len(linked) + len(linked_chains),
        }

    def _origin(self, origin, problems):
        """The `sources` entry for a merge's origin, adding to `problems` when it is not valid."""
        keys = set(origin)
        if keys == {"source"}:
            known = {line.get("id") for line in self.store.read_jsonl("graph/sources.jsonl")}
            if origin["source"] not in known:
                problems.append(f"origin.source {origin['source']!r} is not registered: call register_source")
            return {"source": origin["source"]}
        if keys == {"goal", "log", "step"}:
            goal_id, log_id, step = origin["goal"], origin["log"], origin["step"]
            try:
                exists = isinstance(self.store.read_goal(goal_id), dict)
                log_exists = exists and self.store.path(self.store.log_rel(goal_id, log_id)).exists()
            except store.StoreError as e:
                problems.append(f"origin: {e}")
                return {"goal": goal_id, "log": log_id, "step": step}
            if not exists:
                problems.append(f"origin.goal {goal_id!r} is not a goal")
            elif not log_exists:
                problems.append(f"origin.log {log_id!r} is not a session log of {goal_id}")
            else:
                plan = self.store.read_plan(goal_id)
                steps = [s.get("id") for s in plan.get("steps", [])] if isinstance(plan, dict) else []
                if step not in steps:
                    problems.append(f"origin.step {step!r} is not a step of {goal_id}'s plan")
            return {"goal": goal_id, "log": log_id, "step": step}
        problems.append("origin must be {goal, log, step} for a taught step or {source} for imported notes")
        return {}

    def tool_register_source(self, path, force=False):
        given = Path(os.path.expanduser(path))
        if not given.is_absolute():
            raise ToolError(f"path {path!r} must be absolute")
        real = given.resolve()
        if not real.is_file():
            raise ToolError(f"{real} is not a file")
        digest = hashlib.sha256()
        try:
            with open(real, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 16), b""):
                    digest.update(chunk)
        except OSError as e:
            raise ToolError(f"{real} can't be read: {e}")
        sha = digest.hexdigest()
        lines = self.store.read_jsonl("graph/sources.jsonl")
        source_id = None
        for line in lines:
            if line.get("path") == str(real):
                source_id = line.get("id")
        last = [line for line in lines if source_id and line.get("id") == source_id]
        changed = force or not last or last[-1].get("sha256") != sha
        if source_id is None:
            source_id = store.new_id("src_", taken={line.get("id") for line in lines})
        if changed:
            self.store.append_jsonl("graph/sources.jsonl",
                                    {"id": source_id, "path": str(real), "sha256": sha, "at": store.now()})
        return {"source_id": source_id, "changed": changed, "path": str(real)}

    # Reading logs and opening pages

    def tool_read_session(self, goal_id=None, log_id=None):
        if goal_id is None and log_id is None:
            raise ToolError("pass goal_id, log_id, or both (goal_id left out with a log_id reads a practice log)")
        if goal_id is not None:
            self._goal(goal_id)
        if log_id is None:
            logs = self.store.log_ids(goal_id)
            if not logs:
                return {"goal": goal_id, "log": None, "entries": []}
            log_id = logs[-1]
        elif not self.store.path(self.store.log_rel(goal_id, log_id)).exists():
            where = f"goal {goal_id}" if goal_id else "practice"
            raise ToolError(f"No log {log_id!r} for {where}")
        return {"goal": goal_id, "log": log_id, "entries": self.store.read_log(goal_id, log_id)}

    def tool_open_graph_page(self, goal_id=None):
        if goal_id is not None:
            self._goal(goal_id)
        import graph_page  # another slice; imported only when needed
        path = Path(graph_page.build(self.store, goal_id)).resolve()
        self._open(path)
        return {"path": str(path)}

    def tool_open_in_browser(self, path):
        given = Path(os.path.expanduser(path))
        root = self.store.root.resolve()
        if not given.is_absolute():
            raise ToolError(f"path {path!r} must be absolute, inside the data folder {root}")
        real = given.resolve()
        if real != root and root not in real.parents:
            raise ToolError(f"{path} is outside the data folder {root}: only files inside it can be opened")
        if not real.is_file():
            raise ToolError(f"{real} is not a file")
        self._open(real)
        return {"opened": str(real)}

    def _open(self, path):
        if not open_browser(path):
            raise ToolError(f"No browser could be opened; the file is {path}")


def _chain_view(chain, props):
    def node(pid):
        return {"id": pid, "statement": props.get(pid, {}).get("statement")}

    return {"id": chain["id"], "premises": [node(p) for p in chain.get("premises", [])],
            "conclusion": node(chain.get("conclusion"))}


def _statement(target, props, chains):
    """A due target's statement. A chain reads as its premises, then its conclusion."""
    if target in props:
        return props[target].get("statement")
    if target in chains:
        c = chains[target]
        premises = " + ".join(str(props[p].get("statement")) for p in c.get("premises", []))
        return f"{premises} -> {props[c['conclusion']].get('statement')}"
    return None


def _rpc_error(msg_id, code, message):
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Study's MCP server, over stdio.")
    parser.add_argument("--data-dir", help="The data folder. A leading ~ is expanded; empty means ~/Study.")
    args = parser.parse_args(argv)
    # Protocol messages get a private copy of stdout. Anything else written to stdout, a stray
    # print or a child process such as the browser opener, lands on stderr instead.
    out = os.fdopen(os.dup(1), "wb")
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    server = Server(store.Store(store.resolve_data_dir(args.data_dir)))
    try:
        for line in sys.stdin.buffer:
            if not line.strip():
                continue
            response = server.handle_line(line.strip())
            if response is not None:
                out.write(json.dumps(response, ensure_ascii=False).encode("utf-8") + b"\n")
                out.flush()
    except (BrokenPipeError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    main()
