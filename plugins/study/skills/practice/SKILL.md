---
name: practice
description: Practice ideas Study taught you, with problems that don't say which idea they need. Hints on request, the solution at the end, and a due list that brings weak ideas back.
argument-hint: "[topic]"
disable-model-invocation: true
---

# Practice

Pose practice problems on ideas in the learner's Study graph, one at a time, in plain chat. A check asks about an idea while it is fresh. A practice problem gives no pointer: the learner has to notice which idea applies.

Arguments: `$ARGUMENTS`

Before anything else, read these two files and follow them for the whole sitting:

- `${CLAUDE_SKILL_DIR}/method.md` - how to pick a target, build a problem, give hints, grade answers and record the result.
- `${CLAUDE_PLUGIN_ROOT}/skills/study/voice.md` - how to write.

Tools are `mcp__plugin_study_study__<tool>`. `session_id` is always `${CLAUDE_SESSION_ID}`.

## Stop

If the arguments are `stop`:

1. If a problem is open, conclude it (step 5 below) with `outcome: "movedOn"`.
2. `end_session({session_id: "${CLAUDE_SESSION_ID}"})`.
3. Say in one line that practice has ended. Do nothing else.

## Start

Call `start_session({session_id: "${CLAUDE_SESSION_ID}", mode: "practice", topic: "<the arguments>"})`. With no arguments, leave `topic` out.

From the result, keep:

- `session.log` - this sitting's log id.
- `due` - targets due now, longest overdue first, each with `statement` and `lastOutcome`. This list covers the whole graph, even with a topic; with a topic, take the due targets that fit it first.
- `candidates` - propositions (`id`, `statement`) and chains (`id`, `premises`, `conclusion`) that match the topic, or the whole graph. At most 50 of each. For a chain's statements, call `graph_chains({node_id: "<chain or proposition id>"})`.

If `due` and `candidates` are both empty:

- With a topic, try `graph_find({pattern})` with a shorter pattern or a `*` wildcard (for example `equation*`) and use its matches as candidates.
- If there is still nothing, say there is nothing to practice yet, and that `/study <goal>` or `/import-notes <path>` adds ideas. Call `end_session` and stop.

Then go to the first problem.

## Each problem

1. **Choose.** Pick the target and mode, and set the difficulty (`method.md`: "Choosing the next target", "Modes", "Difficulty").
2. **Commit.** Build the problem and solve it first (`method.md`: "Building a problem"). Then `commit_problem({session_id, statement, mode, targets, cue_class, solution})`. Keep the returned `problem_id`. The call is refused while a problem is open; conclude that one first.
3. **Pose.** Show the statement in plain chat, exactly as committed. Nothing else: no mode, no target, no difficulty, no hint. End the turn. The learner works.
4. **Respond.** For each message from the learner, while the problem is open:
   - **A hint request:** give the next rung (`method.md`: "Hints"). One rung per request. End the turn.
   - **An answer:** grade it against the committed solution. Right: go to step 5. Wrong: say so, point at the first break, nudge (`method.md`: "Wrong answers"), note the miss class, end the turn.
   - **Giving up, or asking for the answer:** go to step 5 with `surrendered`.
   - **Skip, or "give me a different one":** go to step 5 with `movedOn`.
   - **A question about the wording:** answer it without giving the idea away.
   - **Turning to other work:** conclude with `movedOn`, then `end_session`. The hooks log every message while practice is on.
   - **Anything else:** answer briefly. The problem stays open.
5. **Conclude.** `conclude_problem({session_id, problem_id, outcome, verdict, rung, miss_class, retest})`, with the values from `method.md`: "Recording a problem". Conclude only when the learner solved it or ended it.
6. **Reveal.** Show the `solution` the call returns. If they missed, add one line on where the miss was. Don't show due dates unless asked.
7. **Wait.** End the turn. The next problem waits until the learner says to go on. If they ask about the solution first, answer, then wait again.

So a problem has two places where the turn always ends: after the statement, and after the reveal.

## The sitting

- **Open** with one to three easy recall problems.
- **Middle:** switch target on every problem. Never run two in a row on the same target.
- **Keep a list of misses** as you go: problem id, target, miss class. A structural miss also gets a short repair after its reveal (`method.md`: "Wrong answers").
- **Close:** when the learner says in words that they want to stop, first retest every miss on the list in a new form, unless they decline. Then `end_session`.
- `/practice stop` ends at once, with no close. A miss not retested comes back through the due list, because its `retest` was set.

## After compaction

The hook adds a message like `Study practice is on (log <id>), open problem pr_x. Reread skills/practice/method.md before going on.` When it does:

1. Reread `${CLAUDE_SKILL_DIR}/method.md` and `${CLAUDE_PLUGIN_ROOT}/skills/study/voice.md`.
2. If it names an open problem and the summary still holds that problem's statement and solution, carry on with it.
3. If not, conclude it with `movedOn`, `verdict: "dontKnow"` and the highest rung you know of, and pick a new problem.
4. If the list of misses is lost, `read_session({goal_id: null, log_id: "<log id>"})` shows how each problem of this sitting ended.

## Rules that never drop

- Commit before showing. The statement never names its target, and no hint below R3 names it.
- Never reveal the solution before `conclude_problem`.
- One rung per hint request.
- After the reveal, end the turn and wait.
- A wrong answer is called wrong.
