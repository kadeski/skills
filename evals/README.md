# Evals

Scored test cases for the skills in this repo, and the tools to improve a skill against them without fooling yourself. The method follows Anthropic's post on [automating eval design and hillclimbing](https://claude.dev/blog/automating-eval-design-and-hillclimbing/): cases drawn from real use, hard for a reason you can name, graded by checks where possible and by a judge on checkable claims where not, and split into a train set you may study and a test set you may not.

Only doc-lint has cases today. The tutor cases were written for the older file-based tutor and were removed; #52 tracks new ones for the artifact-based skill.

## Run

```
evals/run.py dry doc-lint           grade the untouched fixtures: catches grader bugs, costs nothing
evals/run.py run doc-lint           every case, 3 runs each, on sonnet
evals/run.py run doc-lint --split train --case broken-links --runs 1
evals/run.py rejudge evals/results/<run>     judge the same outputs again and count flipped verdicts
evals/run.py compare evals/results/<old> evals/results/<new>
```

`--model` sets the model the skill runs on, `--judge-model` the judge (both default to sonnet). Compare only runs made with the same models. A doc-lint run took about 15 seconds and $0.08 on sonnet, so a full doc-lint run (8 cases x 3 runs) is roughly $2.

## How a run works

1. `run.py` copies the skill's plugin folder to a temporary folder and adds `evals/<skill>/` to it, since `claude plugin eval` reads cases from below the plugin and evals do not ship in `plugins/`. `claude plugin eval` then starts each run in a clean temporary home: no personal CLAUDE.md, memory or other plugins, so nothing outside the skill shapes the result. The case's `setup.sh` seeds the home from `fixture/`.
2. The agent gets the case's prompt, with Read, Write, Edit and Bash, and any other read-only tools the case lists (doc-lint cases add Agent, for subagents).
3. `run.py` copies what the run left in the home, plus its trace, to `evals/results/<skill>-<time>/<split>/<case>/run<n>/`, then deletes the temporary folder.
4. The case's `grade.py` runs programmatic checks on those files and writes claims. A judge model rules on each claim, seeing the user's message, the final reply, every file the run created or changed, and any file the grader shows it with `r.show`.
5. A run's score is the share of checks and claims that pass. A case's score is the mean of its runs. The suite score is the mean of the cases, shown with a 95% band for run-to-run noise.

Runs that time out, break, or have a tool call denied by the harness are left out of the score and counted as errors, so infrastructure noise does not read as a skill change. Write and Edit are allowed anywhere in the temporary home, since the skill keeps its files in the folder the agent starts in, `~/cwd`.

## Layout

```
evals/
  run.py, seed.py
  results/                    git-ignored
  doc-lint/
    lib.py                    parses the lint report and matches it against the defects a case planted
    train/<case>/             cases the hillclimber may read
    test/<case>/              held out: never read these or their results while editing the skill
      case.yaml               prompt, tags, and why the case is hard
      setup.sh                seeds the run's home from fixture/
      fixture/                the files that exist before the run
      grade.py                checks and claims
```

## Write a case

- **Start from real use.** A case is a moment a user actually hits. Look in your own projects and in bug reports first.
- **Say why it is hard** in `description` before running it. "The model fails it" is not a reason; "the natural move is wrong because the skill says X" is.
- **Fixtures look like a real project.** Dates go in as `{{d}}`, `{{d+3}}` or `{{d-1}}`, in contents or file names, and are filled in from the run's date.
- **Check what code can check:** files written or not, what the report cites, what changed on disk. Write claims only for what needs judgment, as one plain statement each that is either true or false of the files. No 1-to-5 scales.
- **Keep the prompt in double quotes** in `case.yaml`; `run.py` reads it as a JSON string.
- Run `evals/run.py dry <skill> -v`: an untouched fixture should fail most checks, and nothing should crash.
- New cases go in train or test at random. Keep about a third in test.

### doc-lint cases

A doc-lint fixture is a small repo in `fixture/cwd/` with one or two planted defects, and decoys that look wrong but are not. `setup.sh` commits it with no git remote, so the run has no issue tracker and works offline. Keep fixtures free of external URLs: the sandbox blocks the network.

`grade.py` lists each defect as the places a finding may cite (`At(path, needle)`, found by searching the fixture, so line numbers are never hardcoded), the groups it may sit in, and a pattern its fix must match. `lib.grade` then checks that each defect is cited at `file:line`, sits in an allowed group with the right fix, and that the report opens by saying issue state was not checked, ends with counts, cites `file:line` for every finding, flags nothing outside the planted defects (decoys and history files included), and leaves every file in the repo unchanged. Check a new fixture with your own link and path checker first: it should report only the planted defects.

After adding or changing cases or graders, make a new baseline: old scores no longer compare.

## Improve a skill

In Claude Code in this repo, `/hillclimb doc-lint` runs the loop: read train failures, make one change to the skill, rerun, keep it only if it beats the noise. The rules are in `.claude/skills/hillclimb/SKILL.md`.
