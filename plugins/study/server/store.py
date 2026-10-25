"""Reads and writes the Study data folder (spec section 8).

The MCP server, the log hook and the graph page all go through this module.
Standard library only; runs on Python 3.9.

- JSON files are written to a temp file, then renamed.
- JSONL files are append-only, one line per write, under a file lock.
- A data folder with a newer `format` than FORMAT refuses every write.
"""
import contextlib
import json
import os
import random
import re
import string
import tempfile
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None

FORMAT = 1
MARKER_TTL = 24 * 3600
DEFAULT_DATA_DIR = "~/Study"
IDK = "I don't know"
CONFIDENCE = {"Guessing": 10, "Unsure": 40, "Fairly sure": 70, "Sure": 95}
VERDICTS = ("right", "partly", "wrong", "dontKnow", "skipped")

_ALPHABET = string.ascii_lowercase + string.digits
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_random = random.SystemRandom()


class StoreError(Exception):
    """A request the store refuses. The message says what to fix."""


class FormatError(StoreError):
    """The data folder was written by a newer Study plugin."""


def resolve_data_dir(value=None):
    """The data folder: `value`, else CLAUDE_PLUGIN_OPTION_DATA_DIR, else ~/Study.

    An empty value, or a `${...}` placeholder Claude Code left unexpanded, counts as unset.
    A leading `~` is expanded.
    """
    chosen = DEFAULT_DATA_DIR
    for candidate in (value, os.environ.get("CLAUDE_PLUGIN_OPTION_DATA_DIR")):
        if candidate and candidate.strip() and not candidate.strip().startswith("${"):
            chosen = candidate.strip()
            break
    return Path(os.path.expanduser(chosen)).absolute()


def now():
    """The current UTC time as `2026-10-25T18:00:00Z`."""
    return datetime.now(timezone.utc).strftime(_TIME_FORMAT)


def parse_time(text):
    """A time written by now(), as an aware datetime."""
    return datetime.strptime(text, _TIME_FORMAT).replace(tzinfo=timezone.utc)


def rand4():
    return "".join(_random.choice(_ALPHABET) for _ in range(4))


def slug(text, limit=40):
    """Lowercase ASCII words joined by dashes, at most `limit` characters."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    out = "-".join(re.findall(r"[a-z0-9]+", text.lower()))[:limit].strip("-")
    return out or "goal"


def new_id(prefix, taken=()):
    """`prefix` plus 4 random characters, not in `taken`. Prefixes: p_, c_, src_, pr_."""
    while True:
        candidate = prefix + rand4()
        if candidate not in taken:
            return candidate


def check_id(value, what="id"):
    """Returns `value` if it is safe as a file name part, else raises StoreError."""
    if not isinstance(value, str) or not _SAFE_ID.match(value):
        raise StoreError(f"{what} {value!r} is not valid: use letters, digits, '-' and '_' only")
    return value


@contextlib.contextmanager
def _exclusive(handle, path):
    """Holds an exclusive lock on the open file `handle` while the block runs."""
    if fcntl is not None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return
    lock = str(path) + ".lock"
    deadline = time.time() + 10
    while True:
        try:
            os.mkdir(lock)
            break
        except FileExistsError:
            if time.time() > deadline:
                raise StoreError(f"{path} is locked; delete {lock} if no Study process is running")
            time.sleep(0.02)
    try:
        yield
    finally:
        os.rmdir(lock)


def _parse_lines(raw):
    """JSON objects from JSONL bytes. Blank and unreadable lines (a torn last write) are skipped."""
    out = []
    for line in raw.decode("utf-8", "replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            out.append(value)
    return out


class Store:
    """One data folder. Paths passed to the read and write methods are relative to it."""

    def __init__(self, root):
        self.root = Path(root)

    def path(self, *parts):
        return self.root.joinpath(*parts)

    # Format

    def format_version(self):
        """The folder's format number, or None when format.json is missing."""
        data = self.read_json("format.json")
        return None if data is None else data.get("format")

    def check_writable(self):
        """Creates the folder and format.json if missing; raises FormatError on a newer format."""
        version = self.format_version()
        if version is None:
            self.root.mkdir(parents=True, exist_ok=True)
            self._replace(self.path("format.json"), {"format": FORMAT})
        elif not isinstance(version, int) or version > FORMAT:
            raise FormatError(
                f"The data folder {self.root} uses format {version!r}; this Study plugin knows "
                f"format {FORMAT} and will not write to it. Update the plugin."
            )

    # Files

    def read_json(self, rel, default=None):
        path = self.path(rel)
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return default
        except ValueError as e:
            raise StoreError(f"{path} is not valid JSON: {e}")

    def write_json(self, rel, obj):
        self.check_writable()
        self._replace(self.path(rel), obj)

    def _replace(self, path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix="." + path.name + ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, str(path))
        except BaseException:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(tmp)
            raise

    def read_jsonl(self, rel):
        try:
            with open(self.path(rel), "rb") as f:
                return _parse_lines(f.read())
        except FileNotFoundError:
            return []

    def append_jsonl(self, rel, obj):
        """Appends one line under the file lock."""
        self._append(rel, lambda existing: obj, read=False)
        return obj

    def append_entry(self, rel, entry):
        """Appends a session log entry, adding `n` (last n + 1) and `at` under the lock.

        Returns the entry as written.
        """
        def build(existing):
            last = max((e["n"] for e in existing if isinstance(e.get("n"), int)), default=0)
            return dict({"n": last + 1, "at": now()}, **entry)

        return self._append(rel, build, read=True)

    def _append(self, rel, build, read):
        self.check_writable()
        path = self.path(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a+b") as f:
            with _exclusive(f, path):
                if read:
                    f.seek(0)
                    raw = f.read()
                else:
                    size = f.seek(0, os.SEEK_END)
                    if size:
                        f.seek(size - 1)
                    raw = f.read(1) if size else b""
                obj = build(_parse_lines(raw) if read else [])
                line = json.dumps(obj, ensure_ascii=False) + "\n"
                if raw and not raw.endswith(b"\n"):
                    line = "\n" + line
                f.write(line.encode("utf-8"))
                f.flush()
                os.fsync(f.fileno())
        return obj

    # Paths

    def goal_rel(self, goal_id, *parts):
        return str(Path("goals", check_id(goal_id, "goal_id"), *parts))

    def log_rel(self, goal_id, log_id):
        """The session log of `log_id`: under the goal, or under practice/ when goal_id is None."""
        name = check_id(log_id, "log_id") + ".jsonl"
        if goal_id is None:
            return str(Path("practice", "sessions", name))
        return self.goal_rel(goal_id, "sessions", name)

    # Goals

    def new_goal_id(self, title):
        while True:
            goal_id = f"{slug(title)}-{rand4()}"
            if not self.path(self.goal_rel(goal_id)).exists():
                return goal_id

    def new_log_id(self, goal_id=None):
        while True:
            log_id = datetime.now(timezone.utc).strftime("%Y-%m-%d") + "-" + rand4()
            if not self.path(self.log_rel(goal_id, log_id)).exists():
                return log_id

    def read_goal(self, goal_id):
        return self.read_json(self.goal_rel(goal_id, "goal.json"))

    def write_goal(self, goal):
        """Writes goal.json, setting `updated` to now."""
        goal["updated"] = now()
        self.write_json(self.goal_rel(goal["id"], "goal.json"), goal)
        return goal

    def list_goals(self):
        """Every goal.json, most recently updated first."""
        goals = []
        base = self.path("goals")
        if base.is_dir():
            for d in base.iterdir():
                if _SAFE_ID.match(d.name):
                    goal = self.read_goal(d.name)
                    if goal:
                        goals.append(goal)
        goals.sort(key=lambda g: g.get("updated") or "", reverse=True)
        return goals

    def read_plan(self, goal_id):
        return self.read_json(self.goal_rel(goal_id, "plan.json"))

    def write_plan(self, goal_id, plan):
        self.write_json(self.goal_rel(goal_id, "plan.json"), plan)
        return plan

    # Session logs

    def log_ids(self, goal_id=None):
        """The goal's log ids (practice logs when goal_id is None), oldest first by their first entry."""
        folder = self.path(self.goal_rel(goal_id, "sessions") if goal_id else "practice/sessions")
        if not folder.is_dir():
            return []
        keyed = []
        for p in folder.glob("*.jsonl"):
            if _SAFE_ID.match(p.stem):
                entries = self.read_jsonl(str(p.relative_to(self.root)))
                keyed.append(((entries[0].get("at") if entries else "") or "", p.stem))
        return [log_id for _, log_id in sorted(keyed)]

    def read_log(self, goal_id, log_id):
        return self.read_jsonl(self.log_rel(goal_id, log_id))

    def append_log(self, goal_id, log_id, entry):
        return self.append_entry(self.log_rel(goal_id, log_id), entry)

    def goal_entries(self, goal_id):
        """Every entry of every log of the goal, oldest log first, each copied with a `log` field."""
        out = []
        for log_id in self.log_ids(goal_id):
            out.extend(dict(e, log=log_id) for e in self.read_log(goal_id, log_id))
        return out

    # Active markers: <data>/active/<claude-session-id>.json = {mode, goal, log, started}

    def marker_rel(self, session_id):
        return str(Path("active", check_id(session_id, "session_id") + ".json"))

    def write_marker(self, session_id, marker):
        self.write_json(self.marker_rel(session_id), marker)
        return marker

    def read_marker(self, session_id, at=None):
        """The live marker, or None when there is none or it is stale.

        A marker is stale when neither it nor its log changed in MARKER_TTL seconds.
        """
        marker = self.read_json(self.marker_rel(session_id))
        if not isinstance(marker, dict) or not marker.get("log"):
            return None
        at = time.time() if at is None else at
        try:
            last = parse_time(marker["started"]).timestamp()
        except (KeyError, TypeError, ValueError):
            last = 0
        for rel in (self.marker_rel(session_id), self.log_rel(marker.get("goal"), marker["log"])):
            with contextlib.suppress(OSError):
                last = max(last, self.path(rel).stat().st_mtime)
        if at - last > MARKER_TTL:
            return None
        return marker

    def delete_marker(self, session_id):
        with contextlib.suppress(FileNotFoundError):
            os.unlink(str(self.path(self.marker_rel(session_id))))

    # Graph

    def graph(self):
        """(propositions, chains), each an id -> node dict in insertion order.

        Chains whose premises or conclusion no longer exist are left out.
        """
        props = fold(self.read_jsonl("graph/propositions.jsonl"))
        chains = fold(self.read_jsonl("graph/chains.jsonl"))
        chains = {
            cid: c for cid, c in chains.items()
            if c.get("conclusion") in props and all(p in props for p in c.get("premises", []))
        }
        return props, chains


def fold(ops):
    """Folds a graph operation log (spec section 8, Graph) into id -> node.

    Ops: add (the node's fields), source (another place it was taught), alias (another wording),
    delete. Ops on unknown ids are ignored. Every node gets `sources`; propositions get `aliases`.
    """
    nodes = {}
    for op in ops:
        kind, node_id = op.get("op"), op.get("id")
        if kind == "add" and node_id:
            node = {k: v for k, v in op.items() if k != "op"}
            node["sources"] = list(node.get("sources") or [])
            if "statement" in node:
                node["aliases"] = list(node.get("aliases") or [])
            nodes[node_id] = node
        elif node_id in nodes:
            if kind == "source" and op.get("source") is not None:
                nodes[node_id]["sources"].append(op["source"])
            elif kind == "alias" and op.get("text"):
                nodes[node_id].setdefault("aliases", []).append(op["text"])
            elif kind == "delete":
                del nodes[node_id]
    return nodes


# Reading a session log. Each takes the entries of ONE log: question ids are per log.


def open_question(entries):
    """The latest `question` entry with no `answer` and no `verdict` yet, or None."""
    done = {e.get("question") for e in entries if e.get("type") in ("answer", "verdict")}
    for e in reversed(entries):
        if e.get("type") == "question" and e.get("id") not in done:
            return e
    return None


def ungraded(entries):
    """`question` entries that have an `answer` but no `verdict`, oldest first."""
    answered = {e.get("question") for e in entries if e.get("type") == "answer"}
    graded = {e.get("question") for e in entries if e.get("type") == "verdict"}
    return [
        e for e in entries
        if e.get("type") == "question" and e.get("id") in answered and e.get("id") not in graded
    ]


def step_statuses(plan, entries):
    """step id -> upcoming / current / visited (spec section 2, "Where the lesson is").

    `entries` are the goal's entries across all its logs, in order (Store.goal_entries). The
    current step is the step of the latest question tied to a step. Steps before it in plan order,
    and any other step that has had a question, are visited. The rest are upcoming.
    """
    steps = [s.get("id") for s in (plan or {}).get("steps", [])]
    statuses = {s: "upcoming" for s in steps}
    asked = [e["step"] for e in entries if e.get("type") == "question" and e.get("step") in statuses]
    if not asked:
        return statuses
    current = asked[-1]
    for s in steps[: steps.index(current)] + asked:
        statuses[s] = "visited"
    statuses[current] = "current"
    return statuses


def grade(question, picked):
    """Grades picked option labels against the question entry's committed `key`.

    "I don't know" picked: dontKnow. Exactly the key: right. Some of the key: partly. Else wrong.
    """
    picked = set(picked)
    key = set(question.get("key") or [])
    if IDK in picked:
        return "dontKnow"
    if picked == key:
        return "right"
    if picked & key:
        return "partly"
    return "wrong"


def confidence_value(label):
    """10 / 40 / 70 / 95 for a Confidence option label (any case), else None."""
    if not isinstance(label, str):
        return None
    for name, value in CONFIDENCE.items():
        if label.strip().lower() == name.lower():
            return value
    return None
