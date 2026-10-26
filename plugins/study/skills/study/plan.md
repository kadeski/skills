# Plan

The plan is the smallest set of steps from what the learner holds to the goal. The lesson is decided here, so give it real thought. `session_id` is the session id from `SKILL.md`.

## 1. Find the path

Start from the probe in `goal.probe`: each strand's `buildFrom`, its ceiling, and its misconceptions. Work out the reasoning that leads from those held ideas to the goal.

- Nothing the learner holds is taught again.
- Nothing off the path is taught, however interesting.
- A misconception on the path gets repaired where it would break the lesson, inside the step that needs the right idea.
- Some facts can't be derived from what the learner holds. Mark those to yourself: they will be stated plainly. If you are not sure one is true, start the researcher now (`SKILL.md`, Helpers), so the brief is back before you teach it.

## 2. Write the steps

Each step has:

- `id`: `s1`, `s2`, and so on.
- `title`: two to four words.
- `claim`: one full sentence, the idea the step makes obvious. A claim, not a topic: "Undo the last operation first", not "Order of undoing".
- `dependsOn`: the ids of the steps it needs.

A step is a landmark, not a chapter. The lesson crosses it in several small reasoning moves and may check it more than once. Most goals take 3 to 7 steps. The last step's claim is the goal, or the last idea the goal needs.

Before saving, test each step: does its claim follow from what the learner holds, plus the earlier steps, in a few short moves? If not, a step is missing. Does any step teach something the probe showed they hold? Cut it.

## 3. Save and show

Call `save_plan({session_id, goal_id, steps})`. It checks for unique ids, known dependencies and no cycles; fix what it lists and call again.

Show the plan as a numbered list, one line per step: the title and the claim. Then ask in one ungraded AskUserQuestion whether to start or to change something. A change means `save_plan` again with the whole new list, then the task changes below.

Teaching starts with the first question tied to a step. Read `teach.md` and `questions.md`.

## Tasks

Each plan step is one Claude Code task, so the learner sees the plan and where the lesson is.

**Which tools.** Use `TaskCreate`, `TaskUpdate` and `TaskList` when the session has them. If it has `TodoWrite` instead, keep the same list with it: one item per step, each with `content`, `status` and `activeForm`. If it has neither, skip tasks and say nothing about it; `plan.json` holds the plan.

**Statuses.** Each step's status maps to a task status:

| Step status | Task status |
|---|---|
| `upcoming` | `pending` |
| `current` | `in_progress` |
| `visited` | `completed` |

**Create them** after the first `save_plan`:

1. For each step in plan order, `TaskCreate` with `subject` `"<id> <title>"` (like `"s2 Undo in reverse"`), `description` the claim, and `activeForm` `"Learning: <title>"`. Note the task id each one returns, next to its step id.
2. For each step with `dependsOn`, `TaskUpdate` with its `taskId` and `addBlockedBy` set to the task ids of those steps.
3. New tasks start `pending`, which fits a new plan.

**Recreate them on a continued goal.** The plan from `start_session` (or `read_plan({goal_id})`) has each step's status. First call `TaskList`. If tasks for these steps already exist in this session (subjects starting with the step ids), update those. Otherwise create them as above. Then `TaskUpdate` each one whose status is not `pending`: `in_progress` for the current step, `completed` for visited ones.

**While teaching.** When the lesson moves past a step: `TaskUpdate` its task to `completed`, and the next step's task to `in_progress`.

**When the plan changes.** Steps that are gone: `TaskUpdate` with `status: "deleted"`. New steps: `TaskCreate`, with dependencies as above. Changed titles or claims: `TaskUpdate` with the new `subject` or `description`.
