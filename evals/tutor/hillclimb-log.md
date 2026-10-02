# Tutor hillclimb log

One entry per round: date, root cause, the edit, train and test before and after (95% noise band), kept or reverted. Newest last.

## 2026-10-02, round 1 (sonnet)

- Root cause: SKILL.md said "ask one question" without saying that two asks joined by "and" or "so" count as two, so wrong-model feedback often ended with a two-part question.
- Edit: Grading, Wrong model: "ask one question (two asks joined by "and" or "so" are two)".
- Train 0.951 +/- 0.007 -> 0.948; test 0.952 +/- 0.008 -> 0.942 +/- 0.016. Compare: flat, noise band +/- 0.023, says Revert.
- one-question claim misses on train: 10 of 15 -> 3 of 13; wrong-model 0.92 -> 1.00 on every run.
- Runs: tutor-2026-10-02T11-12-21 -> tutor-2026-10-02T12-17-11 (2 runs errored). Outcome: kept (plainly general; targeted misses fell).

## 2026-10-02, round 2 (sonnet)

- Root cause: SKILL.md asks the tutor to work out and check its own numbers (Accuracy) but never the learner's, so grading trusts a worked line that looks right and an arithmetic slip is marked right.
- Edit: top of Grading: "Work out each answer yourself before marking it: a worked line that looks right can hide a slip."
- Train 0.948 -> 0.926 +/- 0.027; test 0.942 -> 0.940 +/- 0.013. Compare: flat, says Revert.
- slip claim on slip-and-gap: 0 of 3 -> 0 of 3; "plan says redo Q1 and Q3": 0 of 3 -> 0 of 3. Every run still wrote "Right" and restated 50 / 250 = 0.25. The rule had no effect.
- Ruler check: rejudge of the baseline flipped 14 of 320 claim verdicts (4%), under the 1 in 10 limit.
- Runs: tutor-2026-10-02T12-17-11 -> tutor-2026-10-02T12-58-30 (1 run errored). Outcome: reverted.

## 2026-10-02, round 3 (sonnet)

- Root cause: same as round 2, read as anchoring: the tutor reads the learner's working first and agrees with it, so a rule to "work it out" does not fire.
- Edit: top of Grading: "Solve each question yourself from the question alone, then compare your result with the learner's final answer: their working can look right and still hold a slip."
- Train 0.948 -> 0.933 +/- 0.019; test 0.942 -> 0.929 +/- 0.027. Compare: flat, says Revert.
- slip claim on slip-and-gap: 0 of 3 -> 0 of 3; "plan says redo Q1 and Q3": 0 of 3 -> 0 of 3. Feedback still restates 50 / 250 = 0.25 as right.
- Runs: tutor-2026-10-02T12-17-11 -> tutor-2026-10-02T13-26-17. Outcome: reverted.
- Stall: two rounds in a row with nothing kept on the same miss. Sorted as a model limit, not a skill gap: two differently worded rules had no effect on 6 of 6 runs, and Opus misses it too (0 of 3 in tutor-2026-10-02T11-37-42).
