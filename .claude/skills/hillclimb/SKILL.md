---
name: hillclimb
description: Improve one skill in this repo against its eval cases in evals/<skill>/, one change per round, keeping a change only when train and test scores rise beyond noise. Use when asked to hillclimb, tune or improve a skill with its evals, or to cut a skill's cost at the same score.
argument-hint: "<skill> [goal: score | cost] [rounds: N]"
---

# Hillclimb

Improve `plugins/<plugin>/skills/<skill>/SKILL.md` against `evals/<skill>/`. Read `evals/README.md` first for how runs and grading work.

## Rules that keep the score honest

- **Never read the test set.** Not `evals/<skill>/test/`, not `evals/results/*/test/`. `run.py` prints only the test aggregate; that is all you get.
- **Never put eval content into the skill.** No case topics, numbers, file names, wording or answers in SKILL.md. A change must be a general rule a new learner on a new topic would benefit from.
- **One change per round,** aimed at a root cause, so a score change can be traced to it. Rewording without a reason is not a change.
- **Do not edit cases or graders mid-climb.** If one is wrong, stop and say so: changing the ruler resets the baseline.
- Prefer making an existing instruction clearer or removing one over adding text. SKILL.md length is a cost every run pays.

## Setup

1. Goal: the user's, or score by default. For cost: same score with a cheaper `--model` or a shorter skill.
2. Baseline: the newest full run of the current SKILL.md in `evals/results/` (its fingerprint matches `sha256` of the file), else `evals/run.py run <skill>`.
3. Check the ruler before climbing:
   - `evals/run.py rejudge <baseline>`. If more than 1 in 10 verdicts flip, the claims are too vague: report which, and stop.
   - A case that scores 1.0 on every run has no headroom; one that swings widely between runs is noise. Note both.
   - If the suite is above 0.95, report that it is saturated and stop: it needs harder cases, not a better skill.
   - With fewer than 5 test cases, a real fix rarely moves test beyond noise, so most rounds will end Unclear. Say so before starting.

## Each round

1. Read the train misses: `grades.json` in `evals/results/<run>/train/*/run*/`, then the run's files under `home/` and its `trace.jsonl` to see why. Look across cases for the same cause.
2. Name the root cause in one sentence, as a gap or ambiguity in SKILL.md, not as a fact about a case.
3. Make one edit to SKILL.md.
4. `evals/run.py run <skill>`, then `evals/run.py compare <previous kept run> <new run>`.
5. Keep the edit if compare says Keep. If it says Unclear, keep only when the edit is plainly general; three Unclear keeps in a row is overfitting: revert to the last clear Keep. Otherwise `git checkout plugins/<plugin>/skills/<skill>/SKILL.md`.
6. Add an entry to `evals/<skill>/hillclimb-log.md`: date, root cause, the edit in one line, train and test before and after with bands, kept or reverted.

Stop after the round limit (default 5), or after 3 rounds in a row with nothing kept. On a stall, edit nothing: sort each remaining train miss into skill gap, bad case, bad grader or noise, with the evidence, and report.

## Finish

Report the start and end scores for train and test with their bands, and each kept edit. Recommend merging only if test rose beyond noise. Merging a SKILL.md change means bumping the version in all three of the plugin's manifests and running `scripts/check.sh`. Do not commit unless asked.
