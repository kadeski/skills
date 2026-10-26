"""The Study hook command (spec section 6, contracts section 6).

`python3 -I log_hook.py <answer|prompt|compact>`, with the hook input JSON on stdin:

- answer (PostToolUse, AskUserQuestion): logs the graded answer, grades multiple choice with code,
  and logs every other answered question as an `ask` entry.
- prompt (UserPromptSubmit): logs the learner's words and links them to an open free-text question.
- compact (SessionStart, compact): says where the lesson is and which phase file to reread.

Every Claude Code session with the plugin enabled runs it, so it exits with no output before
importing anything heavy: before json when no session has a marker file (json alone costs about
25 ms on Python 3.9), and before store when this session has none. It never blocks: it always
exits 0, and errors go to stderr and <data>/errors.log.
"""
import os
import sys
import time

MODES = ("answer", "prompt", "compact")
EVENTS = {"answer": "PostToolUse", "prompt": "UserPromptSubmit", "compact": "SessionStart"}
CONFIDENCE_HEADER = "Confidence"
# Relative to the plugin root. A status not listed (done, or a missing goal.json) gets SKILL.md.
PHASE_FILES = {
    "probing": ["skills/study/probe.md", "skills/study/questions.md"],
    "planning": ["skills/study/plan.md"],
    "teaching": ["skills/study/teach.md", "skills/study/questions.md"],
}
STUDY_FILE = "skills/study/SKILL.md"
PRACTICE_FILE = "skills/practice/method.md"


def quick_data_dir():
    """store.resolve_data_dir() without importing store: the env var, else ~/Study."""
    value = (os.environ.get("CLAUDE_PLUGIN_OPTION_DATA_DIR") or "").strip()
    if not value or value.startswith("${"):
        value = "~/Study"
    return os.path.abspath(os.path.expanduser(value))


def safe_id(value):
    """store.check_id's rule, without the regex: ASCII letters, digits, '-' and '_'."""
    return (
        isinstance(value, str) and value.isascii() and value[:1].isalnum()
        and all(c.isalnum() or c in "-_" for c in value)
    )


def report(mode, message, raw=None):
    """Writes an error to stderr and, when the data folder exists, to its errors.log.

    `raw` (the hook input) is appended after the message line as it came.
    """
    sys.stderr.write(f"study log_hook {mode}: {message}\n")
    try:
        data = quick_data_dir()
        if not os.path.isdir(data):
            return
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(os.path.join(data, "errors.log"), "a", encoding="utf-8") as f:
            f.write(f"{stamp} log_hook {mode}: {message}\n")
            if raw is not None:
                f.write(raw if raw.endswith("\n") else raw + "\n")
    except OSError as e:
        sys.stderr.write(f"study log_hook {mode}: could not write errors.log: {e}\n")


def any_marker():
    """Whether any session has a marker file. With none, no session is studying."""
    try:
        names = os.listdir(os.path.join(quick_data_dir(), "active"))
    except OSError:
        return False
    return any(name.endswith(".json") for name in names)


def main(argv):
    mode = argv[1] if len(argv) == 2 else None
    raw = sys.stdin.buffer.read().decode("utf-8", "replace")
    if mode not in MODES:
        report(mode, f"usage: log_hook.py <{'|'.join(MODES)}>")
        return
    if not any_marker():
        return
    import json
    try:
        data = json.loads(raw)
    except ValueError:
        data = None
    if not isinstance(data, dict) or not isinstance(data.get("session_id"), str):
        report(mode, "could not parse the hook input; raw input follows", raw)
        return
    session_id = data["session_id"]
    marker_file = os.path.join(quick_data_dir(), "active", session_id + ".json")
    if not safe_id(session_id) or not os.path.isfile(marker_file):
        return

    # A marker file exists: from here on store decides whether it is live.
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
    import store

    s = store.Store(store.resolve_data_dir())
    marker = s.read_marker(session_id)
    if marker is None:
        return
    text = HANDLERS[mode](s, store, marker, data, raw)
    if text:
        out = {"hookSpecificOutput": {"hookEventName": EVENTS[mode], "additionalContext": text}}
        sys.stdout.write(json.dumps(out) + "\n")


# answer


def as_dict(value):
    """`tool_response` as a dict: itself, or parsed from JSON text. Else None."""
    import json
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return None
    return value if isinstance(value, dict) else None


def first(sources, key, kind):
    """The first `sources[i][key]` that is a `kind`, else None."""
    for source in sources:
        if isinstance(source.get(key), kind):
            return source[key]
    return None


def lookup(mapping, question):
    """`mapping`'s value for the question's text: exact, else with whitespace trimmed."""
    text = question.get("question")
    if not isinstance(text, str):
        return None
    if text in mapping:
        return mapping[text]
    for key, value in mapping.items():
        if isinstance(key, str) and key.strip() == text.strip():
            return value
    return None


def answer_text(value):
    """An answer as a string. A list of labels is joined the way multi-select joins them."""
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def labels(question):
    """The option labels of an asked question."""
    options = question.get("options") or []
    return [o["label"] for o in options if isinstance(o, dict) and isinstance(o.get("label"), str)]


def parse_answer(answer, options):
    """(picked labels, Other text or None) for an answer string (contracts section 6).

    An answer equal to a label is that label. Otherwise it is split on ", ", and when every part
    is a label those are the picks. Anything else is "Other" text.
    """
    known = {o.strip(): o for o in options}
    if answer.strip() in known:
        return [known[answer.strip()]], None
    parts = [p.strip() for p in answer.split(", ")]
    if all(p in known for p in parts):
        picked = []
        for p in parts:
            if known[p] not in picked:
                picked.append(known[p])
        return picked, None
    return [], answer


def notes(annotations, question):
    value = lookup(annotations, question)
    if isinstance(value, dict):
        value = value.get("notes")
    return value if isinstance(value, str) and value.strip() else None


def is_free(question):
    return bool(question.get("freeText")) or not question.get("options")


def quoted(items):
    return ", ".join(f'"{i}"' for i in items)


def trimmed(question, field="question"):
    value = question.get(field)
    return value.strip() if isinstance(value, str) else None


def on_answer(s, store, marker, data, raw):
    sources = [data.get("tool_input"), as_dict(data.get("tool_response"))]
    sources = [x for x in sources if isinstance(x, dict)]
    questions = first(sources, "questions", list)
    answers = first(sources, "answers", dict)
    if questions is None or answers is None:
        report("answer", "could not read the AskUserQuestion input; raw input follows", raw)
        return None
    annotations = first(sources, "annotations", dict) or {}
    asked = [q for q in questions if isinstance(q, dict)]

    goal, log = marker.get("goal"), marker["log"]
    open_q = store.open_question(s.read_log(goal, log))
    header = CONFIDENCE_HEADER.lower()
    confidence_q = next((q for q in asked if (trimmed(q, "header") or "").lower() == header), None)
    graded_q = None
    if open_q is not None and trimmed(open_q) is not None:
        matches = [q for q in asked if q is not confidence_q and trimmed(q) == trimmed(open_q)]
        graded_q = matches[0] if matches else None
    if graded_q is None or lookup(answers, graded_q) is None:
        graded_q = confidence_q = None  # an unpaired Confidence question is an `ask` like any other

    messages = []
    for q in asked:
        if q is confidence_q:
            continue
        answer = answer_text(lookup(answers, q))
        if answer is None:
            continue
        picked, other = parse_answer(answer, labels(q))
        if q is graded_q:
            confidence = None
            if confidence_q is not None:
                confidence = store.confidence_value(answer_text(lookup(answers, confidence_q)))
            note = notes(annotations, q)
            message = log_graded(s, store, goal, log, open_q, answer, picked, other, confidence, note)
            messages.append(message)
        else:
            s.append_log(goal, log, {
                "type": "ask", "question": q.get("question"), "header": q.get("header"),
                "options": labels(q), "picked": picked, "other": other, "notes": notes(annotations, q),
            })
    return "\n".join(messages) or None


def log_graded(s, store, goal, log, question, answer, picked, other, confidence, note):
    """Writes the `answer` entry and, for a picked option, the code's `verdict`. Returns the message."""
    qid = question["id"]
    free = is_free(question)
    s.append_log(goal, log, {
        "type": "answer", "question": qid, "picked": picked, "other": other,
        "confidence": confidence, "notes": note, "freeText": answer if free else None,
    })
    if free or other is not None:
        return f"{qid}: free-text answer via Other, grade it with record_verdict"
    verdict = store.grade(question, picked)
    s.append_log(goal, log, {"type": "verdict", "question": qid, "verdict": verdict, "by": "code"})
    text = f"{qid}: {verdict} (picked {quoted(picked)}; key {quoted(question.get('key') or [])})"
    if question.get("kind") != "predict":
        names = {v: k for k, v in store.CONFIDENCE.items()}
        text += f", confidence {names[confidence]}" if confidence in names else ", confidence not given"
    return text


# prompt


def one_element(text):
    """True for a prompt that is one XML-like element, such as a <task-notification>."""
    import re
    text = text.strip()
    m = re.match(r"<([A-Za-z_][\w.:-]*)(?=[\s/>])", text)
    return bool(m) and text.endswith("</" + m.group(1) + ">")


def is_command(text):
    """True for a slash command such as `/study stop`: the learner's words, not an answer."""
    import re
    return bool(re.match(r"/[A-Za-z][\w:.-]*(\s|$)", text.strip()))


def on_prompt(s, store, marker, data, raw):
    prompt = data.get("prompt")
    if not isinstance(prompt, str):
        report("prompt", "the hook input has no prompt text; raw input follows", raw)
        return None
    if one_element(prompt):
        return None
    goal, log = marker.get("goal"), marker["log"]
    open_q = store.open_question(s.read_log(goal, log))
    s.append_log(goal, log, {"type": "learner", "text": prompt})
    if open_q is None or not is_free(open_q) or is_command(prompt):
        return None
    s.append_log(goal, log, {
        "type": "answer", "question": open_q["id"], "picked": None, "other": None,
        "confidence": None, "notes": None, "freeText": prompt,
    })
    return f"{open_q['id']}: free-text answer linked, grade it with record_verdict"


# compact


def open_problem(entries):
    """The id of the log's latest `problem` with no `conclude` entry, or None."""
    concluded = {e.get("problem") for e in entries if e.get("type") == "conclude"}
    for e in reversed(entries):
        if e.get("type") == "problem" and e.get("problem") not in concluded:
            return e.get("problem")
    return None


def on_compact(s, store, marker, data, raw):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    goal_id, log = marker.get("goal"), marker["log"]
    entries = s.read_log(goal_id, log)
    if goal_id is None:
        text = f"Study practice is on (log {log})"
        problem = open_problem(entries)
        if problem:
            text += f", open problem {problem}"
        return text + f". Reread {root / PRACTICE_FILE} before going on."

    goal = s.read_goal(goal_id) or {}
    status = goal.get("status") or "unknown"
    text = f'Study is on. Goal "{goal.get("title") or goal_id}" ({goal_id}), phase {status}'
    plan = s.read_plan(goal_id) or {}
    statuses = store.step_statuses(plan, s.goal_entries(goal_id))
    for step in plan.get("steps", []):
        if statuses.get(step.get("id")) == "current":
            text += f', current step {step["id"]} "{step.get("title") or ""}"'
            break
    question = store.open_question(entries)
    if question is not None:
        text += f', open question {question.get("id")} "{question.get("question") or ""}"'
    files = PHASE_FILES.get(status, [STUDY_FILE])
    return text + ". Reread " + " and ".join(str(root / f) for f in files) + " before going on."


HANDLERS = {"answer": on_answer, "prompt": on_prompt, "compact": on_compact}

if __name__ == "__main__":
    try:
        main(sys.argv)
    except Exception:
        import traceback
        report(sys.argv[1] if len(sys.argv) > 1 else None, traceback.format_exc().rstrip())
    sys.exit(0)
