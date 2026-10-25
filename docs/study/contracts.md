# Study - build contracts

`spec.md` is the design. This file pins the interfaces it leaves open, so the parts built in parallel fit together. Where the two disagree, this file wins; say so in your report. `checks.md` holds the results of the section 12 checks.

All six slices are merged. Section 1 records who built what; the rest describes the code as built, so change it with the code.

## 1. Slices

Each slice owns its files and touches nothing else. Everything not listed is the base's.

| Slice | Owns |
|---|---|
| server | `plugins/study/server/study_mcp.py`, `tests/study/test_server.py` |
| hook | `plugins/study/scripts/log_hook.py`, `plugins/study/hooks/hooks.json`, `tests/study/test_log_hook.py`, `tests/study/fixtures/hook/` |
| graph page | `plugins/study/server/graph_page.py` (replace the stub), `plugins/study/skills/graph/SKILL.md`, `tests/study/test_graph_page.py`, `tests/study/fixtures/graph/` |
| teach | `plugins/study/skills/study/` (all six files), `plugins/study/agents/extractor.md` |
| practice | `plugins/study/skills/practice/`, `plugins/study/skills/import-notes/`, `plugins/study/skills/record/` |
| helpers | `plugins/study/agents/researcher.md`, `pdf-reader.md`, `visual-maker.md`, `demo-builder.md`, `plugins/study/scripts/shot.py`, `tests/study/test_shot.py` |

The base owns `store.py`, `tests/study/test_store.py`, the manifests, `README.md` files, `scripts/check.sh`, the marketplace, and `docs/study/`. Don't edit them. If `store.py` has a bug or lacks something, work around it in your own file and report it with a failing case.

Rules for every slice:

- Python: 3.9 or newer, standard library only. No `match`, no `X | Y` types, no `datetime.UTC`, no `zip(strict=)`. Run your tests with both `python3` and `/usr/bin/python3` (3.9.6 on this Mac).
- Entry scripts run as `python3 -I <script>`, so they add the plugin's `server/` folder to `sys.path` themselves before `import store`: `sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))` from `scripts/`, or the script's own folder from `server/`.
- Tests import from `plugins/study/server` the way `tests/study/test_store.py` does, and each test file is self-contained (no shared helper module).
- Style (from `AGENTS.md`): simple terms, plain dashes, never em dashes, no filler. Comments as dense as `store.py`'s.
- Before each commit: `scripts/check.sh` passes (the pre-commit hook runs it). No attribution lines in commit messages.
- Commit on your own branch. Don't push, don't open a PR, don't merge.

## 2. Session ids

Skills pass `${CLAUDE_SESSION_ID}` as `session_id` to every tool that takes one. The hook reads `session_id` from its stdin. The marker `<data>/active/<session_id>.json` joins them. `checks.md` confirms the two are the same UUID.

Skills also know the plugin root as `${CLAUDE_PLUGIN_ROOT}`. They declare no `hooks:` in frontmatter: the hooks are plugin-wide (section 6).

## 3. Server tools

The server owns them; skills, agents and the hook depend on these shapes. Every tool answers one text content item holding JSON. A bad input answers `isError: true` with `{"error": "<what to fix>"}`; list every problem found, not just the first. Calls that need the marker (any tool taking `session_id` except `start_session`) refuse with an error that says to call `start_session` when there is no live marker.

Additions to spec section 9: `session_id` on `save_probe`, `save_plan`, `finish_goal`, `record_verdict`, `record_answer` and `conclude_problem`, because they write to the session log; `goal` and `title` on `save_probe`; `paths` in `start_session`'s result.

- `start_session({session_id, mode = "study" | "practice", goal_text?, title?, goal_id?, topic?})`
  - study, with neither `goal_text` nor `goal_id`: writes nothing; returns `{"goals": [{"id", "title", "goal", "status", "updated"}]}`, unfinished goals, newest first.
  - study, with `goal_id` (open it, even a done goal) or `goal_text` (create it; `title` defaults to the first words of `goal_text`): writes the marker and a `start` entry, and returns `{"session": {"log", "mode"}, "goal": <goal.json>, "plan": <the plan object read_plan returns under "plan", or null>, "lastSitting": [<entries of the goal's newest earlier log>], "graph": <graph_overview for the goal>, "paths": {"goal": "<abs goal folder>", "media": "<abs media folder>"}}`.
  - practice: writes the marker (goal null) and a `start` entry in a new practice log; returns `{"session": {"log", "mode"}, "due": [<the list due_list returns under "due">], "candidates": {"propositions": [{"id", "statement", "lastMode", "lastOutcome"}], "chains": [{"id", "premises", "conclusion", "lastMode", "lastOutcome"}]}, "paths": {"media": "<data>/practice/media"}}`. `due` covers the whole graph; with `topic`, candidates match it the way `graph_find` does; without, all. At most 50 of each. A candidate's `lastMode` and `lastOutcome` are as in `due_list`, null when it was never practiced.
- Session scope: `pose_question`, `save_probe`, `save_plan` and `finish_goal` work only in a study session, and only on that session's goal; `commit_problem` and `conclude_problem` only in a practice session. An optional argument passed as null counts as left out.
- `end_session({session_id})`: logs `end`, deletes the marker; `{"ended": "<log id>"}`, or `{"ended": null}` with no marker.
- `list_goals()`: `{"goals": [{"id", "title", "goal", "status", "updated", "doneAt"}]}`, every goal, newest first.
- `save_probe({session_id, goal_id, strands: [{"name", "floor", "ceiling", "misconceptions": [], "buildFrom"}], summary, goal?, title?})`: `goal` and `title` replace the goal text and title with the concrete version the probe settled. Refused while a question is open. Sets status `planning`, logs `probe`. Returns `{"goal": <goal.json>}`.
- `save_plan({session_id, goal_id, steps: [{"id", "title", "claim", "dependsOn": []}]})`: unique ids, known dependencies, no cycles. Bumps `version`, logs `plan`. Returns what `read_plan` returns.
- `read_plan({goal_id})`: `{"plan": {"goal", "version", "steps": [{"id", "title", "claim", "dependsOn", "status"}]}}` with status `upcoming`, `current` or `visited` from `store.step_statuses`; `{"plan": null}` with no plan.
- `finish_goal({session_id, goal_id, note})`: status `done`, `doneAt` now, logs `end` with `note`, deletes the marker. Returns `{"goal": <goal.json>}`.
- `pose_question({session_id, kind, step_id?, question, options?, explanation, key, multi?, free_text?})`, properties in this order so the explanation is written before the key.
  - `kind` is `probe`, `predict` or `check`. Ungraded `ask` questions never come here; the hook logs them.
  - Multiple choice: `options` 2 to 4 distinct non-empty labels, never "I don't know"; `key` a list of labels from `options`; `multi` true when the key has several (a `multi` question may have one key). The server adds "I don't know" (`store.IDK`) when there are 3 or fewer options, then shuffles.
  - Free text: `free_text: true`, no `options`, `key` a one-item list holding the model answer.
  - The question entry stores the final shuffled `options` and `key` as a list.
  - Closes any open question of this log as `skipped` (a `verdict` entry, `by: "server"`). The first question with a step sets the goal's status to `teaching`.
  - Returns `{"question_id": "q3", "options": [...]}` (no `options` for free text), plus `"closed": "q2"` when it closed one. Question ids are `q<n>`, numbered per log.
- `record_verdict({session_id, question_id, verdict, note?, confidence?})`: `verdict` is `right`, `partly`, `wrong` or `dontKnow`. `confidence` is 10, 40, 70, 95 or null. Logs a `verdict` entry with `by: "teacher"`. Returns `{"question_id", "verdict"}`.
- `record_answer({session_id, question_id, text, confidence?})`: logs an `answer` entry (`freeText: text`). Returns `{"question_id"}`.
- `commit_problem({session_id, statement, mode, targets, cue_class, solution})`: `mode` is `recall`, `discrimination` or `composition`; `targets` are existing proposition or chain ids; `cue_class` is `near`, `far` or `bare` (the practice skill's values; the server takes any short text). Refused while this log has an open problem. Writes the `commit` line and a `problem` entry. Returns `{"problem_id": "pr_x7k2"}`.
- `conclude_problem({session_id, problem_id, outcome, verdict, rung, miss_class?, retest})`: the problem must belong to this log; `solved` takes no rung and `solvedWithHints` needs one; `retest` is a boolean, "bring this target back in a new form". Writes the `conclude` line and a `conclude` entry. Returns `{"problem_id", "solution", "due": [{"target", "due"}]}`.
- `due_list({limit?})`: `{"due": [{"target", "statement", "due", "lastOutcome", "lastMode"}]}`, due now, longest overdue first. `lastOutcome` and `lastMode` come from the target's latest concluded problem (its conclude and its commit). Targets never practiced are not due. After a clean solve the gap is double the gap the previous conclude set. A chain target's statement reads `premise + premise -> conclusion`.
- `graph_overview({goal_id?})`: `{"propositions": n, "chains": n, "byGoal": {"<goal id>": n}, "statements": [{"id", "statement"}]}`, at most 40 statements, the goal's first when `goal_id` is given.
- `graph_find({pattern})`: `{"matches": [{"id", "statement", "aliases"}]}`, at most 50. Case-insensitive. A pattern with no `*` matches as a substring; a pattern with `*` must match the whole statement or alias, with `*` standing for any run of characters (so `*both sides*` searches inside).
- `graph_chains({node_id?})`: `{"chains": [{"id", "premises": [{"id", "statement"}], "conclusion": {"id", "statement"}}]}`, all, or those using `node_id` as a premise or conclusion.
- `graph_merge({origin, propositions, chains})`: see section 5.
- `register_source({path, force?})`: `{"source_id", "changed", "path"}`. The same absolute path (symlinks resolved) keeps its source id; `changed` is true when its sha256 differs from the last line for that id, it was never registered, or `force` is true, and then a line is appended. The line is written before extraction, so `/import-notes --force` is how a file whose extractor failed gets retried.
- `read_session({goal_id?, log_id?})`: `{"goal", "log", "entries"}`; with no `log_id`, the goal's newest log; `goal_id` null with a `log_id` reads a practice log.
- `open_graph_page({goal_id?})`: calls `graph_page.build(store, goal_id)` and opens the file. Returns `{"path"}`.
- `open_in_browser({path})`: opens a file inside the data folder (after resolving symlinks); refuses any other path. Returns `{"opened": "<abs path>"}`.

The full MCP tool names are `mcp__plugin_study_study__<tool>`.

## 4. Log entries

Spec section 8 holds, with these additions:

- `verdict` may carry `confidence` (when the teacher maps it from words), and `by` may be `server` (a question closed as `skipped`).
- `answer` always has `picked`, `other`, `confidence`, `notes` and `freeText`. From AskUserQuestion, `picked` is a list of labels (empty for an "Other" answer); for a free-text answer linked from a prompt or given through `record_answer`, `picked` is null and the text is in `freeText`.
- `end` may carry `note` (from `finish_goal`).
- `extracted` is logged in the origin's session log for a step origin, with `propositions` and `chains` as the lists of ids the merge touched; a source origin logs nothing.
- Practice: `problem` is `{problem}` (the problem id) and `conclude` is `{problem, outcome, verdict}`. Lines in `practice/problems.jsonl` carry `type` (`commit` or `conclude`) and `at`.
- Marker: `{"mode": "study" | "practice", "goal": "<goal id>" | null, "log": "<log id>", "started": "<time>"}`.

Use `store.now()` times, `store.open_question` for the open question, `store.grade` for multiple choice, `store.confidence_value` for the Confidence labels, and `store.step_statuses` for step positions.

## 5. `graph_merge`

```json
{
  "origin": {"goal": "two-step-equations-k3f9", "log": "2026-10-25-a1b2", "step": "s2"},
  "propositions": [
    {"key": "a", "statement": "Subtracting the same number from both sides keeps an equation true"},
    {"key": "b", "statement": "...", "same_as": "p_x7k2"}
  ],
  "chains": [{"premises": ["a", "p_q4r1"], "conclusion": "b"}]
}
```

- `origin` is `{goal, log, step}` for a taught step or `{source}` (a `src_` id) for imported notes. It becomes the node's `sources` entry.
- `key` is local to the call. Chain ends are local keys or existing `p_` ids.
- `same_as` links to an existing proposition instead of adding one: a `source` op, plus an `alias` op when the wording differs.
- A statement that equals an existing statement or alias (case and spacing ignored) counts as `same_as` that one. A chain with the same premise set and conclusion as an existing one gets a `source` op instead of a new chain.
- Returns `{"ids": {"a": "p_...", "b": "p_x7k2"}, "added": {"propositions": n, "chains": n}, "linked": n}`.

## 6. The hook

The hook owns these messages; the skills tell the teacher how to read them. Output is `{"hookSpecificOutput": {"hookEventName": "<event>", "additionalContext": "<text>"}}`.

Registration: `plugins/study/hooks/hooks.json`, plugin-wide, because skill frontmatter hooks don't get the data folder, don't survive a resume and don't fire on compaction (`checks.md`). It registers `python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/log_hook.py" <answer|prompt|compact>` for PostToolUse with matcher `AskUserQuestion`, UserPromptSubmit, and SessionStart with matcher `compact`, in exec form (`"command": "python3"` with `args`, as the hooks docs advise when a path placeholder appears) and a 10 second timeout. Every Claude Code session with the plugin enabled runs it, so with no live marker it must exit fast and silent. The data folder is `store.resolve_data_dir()` (the env var, else `~/Study`).

Prompts the learner didn't type also reach UserPromptSubmit, for example a background agent's `<task-notification>…</task-notification>`. A prompt that is one XML-like element (it starts with `<name` and ends with `</name>`, after trimming) is not logged and never linked to a question. A slash command such as `/study stop` is logged as `learner` but never linked.

AskUserQuestion PostToolUse input. `questions` and `answers` are confirmed (`checks.md`); `annotations`, multi-select joining and "Other" are assumed until the hand check:

```json
{
  "session_id": "…", "hook_event_name": "PostToolUse", "tool_name": "AskUserQuestion",
  "tool_input": {
    "questions": [{"question": "…", "header": "…", "options": [{"label": "…", "description": "…"}], "multiSelect": false}],
    "answers": {"<question text>": "<label> | <label>, <label> | <typed Other text>"},
    "annotations": {"<question text>": {"notes": "…"}}
  },
  "tool_response": "…"
}
```

Read `answers` and `annotations` from `tool_input`, else from `tool_response` (as a dict, or JSON text). A multi-select answer is labels joined by `", "`: an answer that equals a label is that label; otherwise split on `", "`, and if every part is a label those are the picks; otherwise it is "Other" text. When the input can't be parsed, append the raw input to `errors.log` and exit 0 with no output.

Matching: the graded question is the open question whose `question` text equals the asked question's text (whitespace trimmed). The confidence question has the header `Confidence` and options Guessing, Unsure, Fairly sure, Sure.

Messages:

- Multiple choice, graded by code: `q7: wrong (picked "B-side"; key "A-side"), confidence Sure`. Several labels: `picked "A", "B"; key "A", "C"`. No confidence answered on a `probe` or `check`: `confidence not given`. A `predict` has no confidence part.
- "Other" text on a graded question: `q7: free-text answer via Other, grade it with record_verdict`.
- Free-text answer in chat (prompt hook): `q9: free-text answer linked, grade it with record_verdict`.
- Compact (study): `Study is on. Goal "<title>" (<goal id>), phase <status>, current step <id> "<title>"[, open question q3 "<text>"]. Reread <phase file> before going on.` Practice: `Study practice is on (log <id>)[, open problem pr_x]. Reread skills/practice/method.md before going on.`
- Phase files, given as absolute paths under the plugin root: `probing` = `skills/study/probe.md` and `skills/study/questions.md`, `planning` = `skills/study/plan.md`, `teaching` = `skills/study/teach.md` and `skills/study/questions.md`, any other status = `skills/study/SKILL.md`. The current step part is left out while no question has a step.

## 7. `graph_page.build`

`build(store, goal_id=None)` writes `<data>/graph.html` and returns its `Path`. `store` is a `store.Store`. It reads `store.graph()`, `store.list_goals()` and the sources in `graph/sources.jsonl`. It never opens a browser; the server does.

## 8. `shot.py`

`python3 -I scripts/shot.py <file> <png> [--width 1280] [--height 800] [--dark]`:

- exit 0: screenshot saved; each console error or page error printed as one line, `console: <text>`
- exit 2: bad arguments, or the page failed to load (message on stderr)
- exit 3: Python Playwright or its Chromium is not installed

Builders call it for a desktop width and again with `--width 390`, and with `--dark` when the page has a dark mode.

## 9. Agents

Plugin agents live in `plugins/study/agents/` and have `model: sonnet` and `background: true`. They name Study tools by full name, for example `mcp__plugin_study_study__graph_find`; a background plugin agent can call them (`checks.md`). Each one's final message is its result: short, no preamble.

`${CLAUDE_PLUGIN_ROOT}` is not relied on inside agent files. The teacher's spawn prompt for visual-maker and demo-builder gives `plugin root: <path>` (from the skill's `${CLAUDE_PLUGIN_ROOT}`), `output: <abs path>` and the brief; the builders run `python3 -I <plugin root>/scripts/shot.py`. The extractor's spawn prompt gives `goal`, `log` and `step` ids and the step's teaching text copied as taught (or `source` id and `path` for notes).
