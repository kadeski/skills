# Questions

How to ask, log and grade every question. `session_id` is the session id from `SKILL.md`. Tool names are short here; the full names are `mcp__plugin_study_study__<tool>`.

## Kinds

| Kind | When | Graded | Step | Asked with |
|---|---|---|---|---|
| `ask` | Any phase: the goal, preferences, plan changes, which goal | No | No | AskUserQuestion; up to 4 questions in one call |
| `probe` | Probe | Yes | Never | AskUserQuestion, or chat for free text |
| `predict` | Before a step, to make the learner reason toward it | Yes | Required | AskUserQuestion |
| `check` | After a step | Yes | Required | AskUserQuestion, or chat for free text |

An `ask` never goes through `pose_question`: call AskUserQuestion directly and the hook logs it.

Use multiple choice when the idea comes down to telling a few options apart. Use free text when the learner has to explain why, derive something, or produce an answer that options would give away.

## A graded multiple-choice question

1. **Commit the key.** Call `pose_question`. Write the properties in this order, so the explanation is written before the key:

   ```json
   {
     "session_id": "<session id>",
     "kind": "check",
     "step_id": "s2",
     "question": "Solve 3x + 4 = 19. What is x?",
     "options": ["5", "15", "23/3"],
     "explanation": "Subtract 4 from both sides: 3x = 15. Divide both sides by 3: x = 5. 15 forgets to divide; 23/3 adds the 4 instead of taking it off.",
     "key": ["5"],
     "multi": false
   }
   ```

   - `kind` is `probe`, `predict` or `check`. `step_id` is required for `predict` and `check` and left out for `probe`.
   - `options`: 2 to 4 distinct, non-empty labels. Each wrong option is a real wrong idea a learner might hold, ideally one the probe found. Keep options alike in length and form. No "all of the above".
   - `key`: a list of labels copied exactly from `options`. `multi: true` only when the key has more than one label. With `multi: true`, no label may hold ", ": that is how the picks of a multi-select answer are joined.
   - The server adds "I don't know" when there are 3 or fewer options, shuffles them, and returns `{"question_id": "q3", "options": [...]}`.
   - `"closed": "q2"` in the result means an earlier question had no answer and was logged as skipped. Expect that only when you meant to drop it.
   - An error lists what to fix. Fix it and call again.

2. **Ask it.** Write the teaching that leads to the question in the chat message, then call AskUserQuestion in the same turn. Here the server returned `["15", "I don't know", "5", "23/3"]`:

   ```json
   {"questions": [
     {"question": "Solve 3x + 4 = 19. What is x?",
      "header": "Equations",
      "multiSelect": false,
      "options": [
        {"label": "15", "description": ""},
        {"label": "I don't know", "description": ""},
        {"label": "5", "description": ""},
        {"label": "23/3", "description": ""}]}
   ]}
   ```

   - `question`: exactly the text you sent to `pose_question`, character for character. The hook finds the open question by this text.
   - `options`: the labels `pose_question` returned, in the returned order, exactly as written, "I don't know" included. `multiSelect` is the `multi` you sent.
   - Option descriptions are empty, or one neutral word if the tool needs text. Never a hint.
   - `header`: a short topic word, 12 characters or fewer, that gives nothing away.
   - Nothing else goes in the same call: one graded question only.

3. **Read the hook message.** After the answer, a hook message arrives with the tool result:

   - `q3: wrong (picked "23/3"; key "5")`. The verdict word is `right`, `partly`, `wrong` or `dontKnow` (they picked "I don't know"). Several labels look like `picked "A", "B"; key "A", "C"`.
   - Code graded it and logged the verdict. Don't call `record_verdict` for it.
   - `q3: free-text answer via Other, grade it with record_verdict`: the learner typed their own answer. Grade it (below) and call `record_verdict`.

4. **Ask for the thinking when it matters.** The learner's thinking is the main evidence, more than right or wrong, but a picked option doesn't show it. After the verdict, ask in chat how they got there when it matters: a wrong answer whose cause you can't tell, or a right answer you doubt. Ask in one short line, and not after every answer.

## A graded free-text question

1. **Commit the key.** Call `pose_question` with `free_text: true`, no `options`, and `key` as a one-item list holding the model answer:

   ```json
   {
     "session_id": "<session id>",
     "kind": "check",
     "step_id": "s1",
     "question": "Why does subtracting 4 from both sides keep 3x + 4 = 19 true?",
     "explanation": "Both sides name the same number. Taking 4 from the same number on each side leaves the same number on each side.",
     "key": ["Both sides are equal, and taking the same amount from equal amounts leaves equal amounts."],
     "free_text": true
   }
   ```

2. **Ask it in chat.** End your message with the question. Then end the turn.
3. **Read the hook message.** The learner's next message comes with `q9: free-text answer linked, grade it with record_verdict`. Grade it and call `record_verdict`.
4. **A message that isn't an answer** gets linked too, such as a question back, or "stop". Reply to it. If the question still stands, pose it again with `pose_question`, which gives it a new id, and leave the old id ungraded. Never invent a verdict for a non-answer.

## When no hook message arrives

The hook can miss an answer. When an answer comes in with no hook line about it:

- Multiple choice: call `record_answer({session_id, question_id, text})` with the picked labels as `text`, then grade it against the key you committed and call `record_verdict`.
- Free text: call `record_answer` with the learner's answer as `text`, then grade it and call `record_verdict`.
- When the hook line is there, never call `record_answer`.
- If the learner skips AskUserQuestion and answers in chat instead, treat that message as the answer the same way: `record_answer`, then `record_verdict`.

## Grading text

`record_verdict({session_id, question_id, verdict, note})`:

- `right`: the answer holds the key's idea, in any words.
- `partly`: some of the key's idea is there and some is missing, or the right answer with a wrong reason.
- `wrong`: the answer contradicts the key, or holds a different idea.
- `dontKnow`: they say they don't know, or make no attempt.
- `note`: one line on what was there and what was missing.

Grade against the key and the explanation you committed, not against a new idea of the answer.

## Giving the verdict

Open with the verdict, plainly: "Right.", "Partly.", "Wrong." For "I don't know", skip the verdict word and go to the missing piece. Then read the answer, with its reasoning when there is any, and act:

| Answer | What it means | Do |
|---|---|---|
| Right, and the reasoning holds or there is none to read | Held | Move on |
| Right, but the reasoning shows a guess or a shaky reason | Fragile | Give the reason in a line. Check it again later, in a new form |
| Right for a wrong reason | A misconception | Treat it as a wrong answer that rests on a wrong idea, below |
| Wrong, and the answer or the reasoning shows a wrong idea (a wrong option that names one, or the same wrong answer again) | A misconception | Stop. Find the wrong idea, show where it breaks, repair it, check again in a new form before building on it |
| Wrong with no sign of an idea behind it, or "I don't know" | A gap | Teach the missing move, then check again |
| Partly | Part held | Say which part holds and which is missing. Teach the missing part |

In the probe, give the verdict in one line and don't teach yet (`probe.md`). After a `predict`, the verdict still comes first; a wrong prediction is where the step starts, not a failure.

Never pose the next question until this one is graded.
