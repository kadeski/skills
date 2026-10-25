# Probe

The probe measures two things: what the goal is, exactly, and where the learner's understanding stops. It teaches nothing. Ask with the protocol in `questions.md`. `session_id` is the session id from `SKILL.md`.

## 1. Start from the graph

`start_session` returned `graph`, an overview of what earlier goals taught. Search it for the goal's key terms with `graph_find`. Don't probe an idea the learner already got solid in an earlier goal. The graph records what was taught, not what was mastered, so when such an idea is central to this goal, one quick question confirms it still holds.

## 2. Make the goal concrete

"Understand LLMs" can mean ten different goals. Find the one this learner means with ungraded `ask` questions: what they want to be able to do or explain, what it is for, what they have met so far. Group up to 4 in one AskUserQuestion call, with likely answers as options.

Stop when the goal fits in one sentence that names what will feel obvious, and the learner agrees with it. For example, "Solve ax + b = c for x and say why each step keeps the equation true", not "Learn algebra".

## 3. List the strands

A strand is one separate thing the goal depends on. "Solve ax + b = c and say why" depends on what an equation claims, on inverse operations, and on the order to undo them in. Most goals have 2 to 5 strands. Keep the list to yourself.

## 4. Find the edge of each strand

Bracket each strand, one graded `probe` question at a time:

- **The floor** is something the learner reliably gets right.
- **The ceiling** is something they get wrong or don't know.
- Start near the top of what the goal needs, not at the basics. Most learners hold more than the basics, and every basic question spends their patience.
- Right and sure: jump up. If they hold the strand at the level the goal needs, the strand is done.
- Right but unsure: step up gently, and note that this part is shaky.
- Wrong: come back down until they get one right. That pins the edge.
- The edge is pinned when the floor and the ceiling are about one reasoning step apart.

A wrong answer is one of three things. Tell them apart before you move on:

- **A slip:** they hold the idea but misread or miscounted. The same idea in a new form goes right.
- **A gap:** they never had the idea. It shows as "I don't know", or as a wrong answer they were unsure of.
- **A misconception:** they hold a wrong idea, often sure of it, and it gives the same wrong answer each time. Dig into these most. Find the wrong rule in their own words: a free-text question ("How did you get that?") shows it best. A misconception left in place breaks every step built on top of it.

Never re-ask what an answer already showed. One answer often shows the edge of two strands. Count it for both.

Most strands take 2 to 4 questions. Stop a strand once its edge is pinned.

## 5. Give verdicts, not lessons

After each answer, give the verdict in one plain line: "Right." or "Wrong." Name the right answer only when that gives nothing away for a later probe question. Don't explain or repair yet: the plan decides what gets taught, and teaching now spoils the measurement. If the learner asks why, say it comes up in the lesson.

## 6. Save it

When every strand has its edge, make sure no question is open: the last answer has its verdict. Then call:

```json
{
  "session_id": "<session id>",
  "goal_id": "<goal id>",
  "goal": "Solve ax + b = c for x and say why each step keeps the equation true",
  "title": "Two-step equations",
  "strands": [
    {"name": "Inverse operations",
     "floor": "Undoes x + 5 = 12 by subtracting 5",
     "ceiling": "In 3x + 4 = 19, divides only the 3x by 3 and gets x + 4 = 19/3",
     "misconceptions": ["Doing something to one term of a side counts as doing it to the whole side"],
     "buildFrom": "Subtracting the same number from both sides of x + 5 = 12"}
  ],
  "summary": "Holds one-step equations. In two-step ones, divides one term instead of the whole side."
}
```

- `save_probe` with `goal` and `title` set to the concrete goal from step 2.
- `floor` and `ceiling`: what the learner did, as specific as the answers showed.
- `misconceptions`: each wrong idea as the learner holds it, in plain words. An empty list when none showed.
- `buildFrom`: the held idea the lesson for this strand starts from.
- `summary`: one or two sentences.

Don't show the result as a report. Go on to the plan: read `plan.md`.
