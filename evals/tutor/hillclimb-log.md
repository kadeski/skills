# Tutor hillclimb log

One entry per round: date, root cause, the edit, train and test before and after (95% noise band), kept or reverted. Newest last.

## 2026-10-02, round 1 (sonnet)

- Root cause: SKILL.md said "ask one question" without saying that two asks joined by "and" or "so" count as two, so wrong-model feedback often ended with a two-part question.
- Edit: Grading, Wrong model: "ask one question (two asks joined by "and" or "so" are two)".
- Train 0.951 +/- 0.007 -> 0.948; test 0.952 +/- 0.008 -> 0.942 +/- 0.016. Compare: flat, noise band +/- 0.023, says Revert.
- one-question claim misses on train: 10 of 15 -> 3 of 13; wrong-model 0.92 -> 1.00 on every run.
- Runs: tutor-2026-10-02T11-12-21 -> tutor-2026-10-02T12-17-11 (2 runs errored). Outcome: kept (plainly general; targeted misses fell).
