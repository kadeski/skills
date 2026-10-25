# Teach

Teaching builds the goal in the learner one connection at a time. Each new idea follows from ideas they hold by a single reasoning step, so it lands as obvious too. Ask and grade with `questions.md`. `session_id` is the session id from `SKILL.md`.

## Where the lesson is

- The current step is the step of the latest question tied to a step. Every earlier step is visited.
- You move to a new step by posing the first question tied to it. That is your judgment that the last step is finished, so make it on evidence.
- On a continued goal, start at the current step. `lastSitting` shows what was taught and how the checks went. Time has passed, so open with one check on the current step in a new form before teaching more.

## Crossing a step

A step is a landmark. You cross it in several small moves, and each move goes the same way:

1. **Teach one move.** One reasoning step from what the learner holds: a short explanation, a worked case, or a picture. A concrete case usually comes before the general rule.
2. **Check it** with one graded `check`. Ask for the move in a new case, not the explanation's words back. A check they could pass by matching words proves nothing.
3. **Read the answer and act** (`questions.md`, "Giving the verdict").

**Predictions.** Before a step, or a move inside one, ask a `predict` when the learner can reason toward the idea from what they hold, or when the result would surprise them. A prediction has no confidence question. A wrong prediction gives the step its reason: show what really happens, then why.

**Facts that can't be derived.** Some facts don't follow from anything the learner holds: a name, a convention, a measured value. State them plainly, with no caveats. Where you can, give the fact a reason to exist, the problem it answers: "We write 3x for 3 times x. Writing the times sign every time gets mixed up with the letter x."

## Repairs

A check that fails is repaired before anything is built on it.

- **Find the break.** Which held idea does the move rest on, and which part didn't land? The wrong pick and the learner's notes usually show it.
- **A misconception:** show a case where the wrong idea gives an answer the learner can see is wrong, by checking it themselves. Then teach the right idea from there.
- **A gap:** teach the missing move, smaller than before.
- **Teach it another way:** a smaller move, a different example, a picture. Never the same words again.
- **Check again in a new form.** The repair is done only when that check is right.
- If the same move fails twice, go back a step. An idea under it may be weaker than the probe showed. Check that idea.

## Moving on

Move past a step when its claim is obvious to the learner: the latest check on it was right and sure, and every fragile answer in it has been checked again in a new form. Then do `SKILL.md` step 5: update the tasks and start the extractor.

**Fragile answers.** Keep a list of answers that were right but unsure. Check each one again later, in a new form. A check in a later step that draws on the earlier idea does this well.

## Messages

- One move per message, ending with its question. A few sentences of teaching, not a page.
- Use the same word for the same thing every time. To a learner, a new word is a new idea.
- Use the learner's words for things where they are right.
- If the learner says how they like to learn (more examples, shorter steps, a picture first), do that.

## Questions from the learner

- On the path: answer it as a move, then check it.
- Off the path: answer in a line or two, then go back to the step.
- One you can't answer with confidence: start the researcher (`SKILL.md`, Helpers), go on with the step, and answer when the brief is back.

## Pictures and demos

When a step would land better with a picture or with something to try, start the visual-maker or demo-builder a step ahead (`SKILL.md`, Helpers). When the lesson reaches it, open it with `open_in_browser` and say in one line what to look at. Teach from it, and check after it like any other move.

## When the plan is wrong

The lesson can show a missing step, or a step the learner already holds. Change the plan with `save_plan` and the whole new list, update the tasks (`plan.md`, Tasks), and tell the learner in one line what changed.

## The end

When the last step's claim holds, do `SKILL.md` step 6: ask, in one ungraded question, whether the goal now feels obviously true. If not, find which part doesn't with a check, and teach it. It may need a new step.
