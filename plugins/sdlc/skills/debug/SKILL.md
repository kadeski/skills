---
name: debug
description: Debug loop for a bug, crash, regression, failing test or wrong output. Reproduce it end to end first, trace it to the layer that owns the fix (where the wrong value is made, not where it shows up), lock it with a failing regression test, fix, and show before and after evidence. Use whenever the user reports something broken or behaving wrong, even if they don't say "debug".
argument-hint: "[symptom or issue]"
disable-model-invocation: true
---

# debug

Bug: $ARGUMENTS

This loop guards against fixing the symptom instead of the cause. In a study of 19 coding agents, 12 bugs that were easy for humans beat every agent, and in 10 of them the best agent found the right file but patched the caller, consumer or display instead of the callee, producer or serializer. Its own tests passed because they checked the wrong level.

## 1. Pin the symptom

Expected vs actual, the exact error text, where it shows up, and since when (a recent commit?). If something essential is missing, ask once, briefly.

## 2. Reproduce end to end, before anything else

- Trigger the bug through the real entry point a user hits: run the app, the CLI command, the request, the UI flow. Capture the failing output. A unit test you wrote yourself is not a reproduction yet.
- Can't reproduce it: stop and report what you tried. Don't fix blind.
- Truly can't run it end to end (prod-only data, hardware): say so, reproduce at the closest level you can, and label it as such.

## 3. Trace to the cause

- Read from the symptom back to where the wrong value or state is first produced. Remove any temporary logging afterwards.
- No edits until you can state the cause in one line: `cause: <what> at file:line · shows up at: file:line`.

## 4. Pick the layer

Fix where the wrong thing is produced, not where it's noticed. Example: matplotlib's DPI doubled on every unpickle. Agents edited 4 display backends to undo the doubling; the real fix was 3 lines that saved the original DPI when pickling. If the fix has to go downstream (you don't own the producer, it's a hotfix), say so and why.

## 5. Lock it, then fix

1. Write a regression test at the cause's level. Run it and show it fails for the right reason.
2. Make the smallest fix. Don't change the test to make it pass.
3. Run the regression test, the end-to-end reproduction from step 2 (now correct), and the full suite.
4. Search for the same class of bug elsewhere (same pattern, same misuse). List the instances. Fix them if they're clearly in scope, otherwise ask.

## 6. Report

- **Cause** (file:line) and why it happened, in plain words and short enough that the user could explain this bug without the agent.
- **Fix**, and why that layer.
- **Evidence**: the reproduction before and after, and the test output.
- **Other instances** found.
- If the bug came from a mistake that could recur (a misread convention, a missing check), suggest /lesson.

## Stuck

When a fix fails and your next attempt would repeat an idea you already tried, stop. Write a short prompt with the symptom, the reproduction, and what's ruled out, and suggest `/clear` and starting over with it. A session that starts from what's ruled out isn't anchored on the theories that failed.
