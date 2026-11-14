---
name: slice
description: Build a spec test-first without stopping for review, then have it reviewed. Each thin vertical slice gets a failing test shown as proof, the smallest code that passes it, the full checks, and a commit as a save point. A Tier 3 spec is built ticket by ticket the same way. When the spec is finished, the /verify review runs by itself. Use when the user types /slice, asks to build a spec, a ticket or the next slice, or wants something built test-first (TDD).
argument-hint: "[spec path] [slice or ticket]"
disable-model-invocation: true
---

# slice

Build the open work in a spec, test-first. Arguments: $ARGUMENTS (both optional: the spec path, and a slice or ticket number to build only that one).

The run is hands-off. The user comes back to a built and reviewed spec with the evidence for each slice, so don't stop along the way to ask for a review. Two rules make that safe:

- The test exists and fails before the code does. When code and its test come out of one step, neither checks the other (MathWorks: a test passed because the code just copied the baseline file to the output).
- Every slice ends in a commit. A bad slice gets reverted, not dug out of.

## What to build

- **Spec**: the path given, else the spec marked `Status: building` in `docs/specs/` (or where CLAUDE.md keeps specs).
- **Slices** (Tier 2): every unticked slice in order, or only the one whose number was given.
- **Tickets** (Tier 3): every unticked ticket in order, or only the one named. When a ticket starts, split it into 2-4 thin vertical slices, write them under the ticket in the spec, and build them. When they're done, run the ticket's done-when check, show its output, and tick the ticket.
- **No spec**: build to the done-when check you were handed (a /next contract carries one). With none, ask for a one-line done-when check before starting. If the change is bigger than a small fix, suggest /spec.

## Where the work lands

A PR is worth opening only where CI checks it. Decide once, before the first edit:

- **The repo has a remote (`git remote`) and a CI workflow** (a file in `.github/workflows/`): the work goes on a branch and ends in a PR. If you are already on a branch other than the default one (a Claude Code Projects thread gets its own branch and PR), use it. Else create a branch named for the spec slug (`git switch -c <spec slug>`).
- **Otherwise**: commit on the current branch and don't push. Without CI a PR checks nothing.

Before the first edit, read the code the work touches and the closest existing work the spec names, and follow its patterns. Run the project's checks once and note what already fails, so you neither blame a slice for those failures nor claim them as fixed.

**One task per slice.** The TaskCreate and TaskUpdate tools may be deferred: if they aren't in your tool list, search for them (ToolSearch) before deciding you have none. If you have them, create one task per slice before building it, named `<spec slug>: slice <N> <behavior>` (for a Tier 3 ticket, when you have written its slices). Mark it in progress when the slice starts and completed in step 4. A project's `TaskCompleted` hook runs its checks when a task is completed and refuses the completion while they fail, so the slice is checked by the project and not only by you. Without the task tools, skip this; the steps are the same.

## Each slice

1. **Write the failing test.** It asserts what the spec's slice line says, at the level that owns the behavior: a producer's job gets a producer test, not a check on the screen that displays it. Run it. It must fail on the assertion, not on an import error, a typo or a missing fixture. Show the test and its failing output as proof, then keep going. If the project asks for a red commit (its CLAUDE.md or rules say to commit the failing test before the code), commit the test now, with any empty stub it needs to fail on its assertion, as `<spec slug>: slice <N> red`.
2. **Make it pass** with the smallest code that does, without editing the test.
3. **Run the checks**: the new test, then the project's full checks (tests, types, lint, build, as CLAUDE.md lists them). Show each command and the tail of its output. "All tests pass" without output is not evidence.
4. **Save**: mark the slice's task completed. If a hook refuses it, the refusal carries the failing output: fix the cause the way step 2 does (never by editing the test), run the checks again, and mark it completed again. Then tick the slice in the spec and commit locally as `<spec slug>: slice <N> <behavior>` (with the ticket ID in front of `slice` in a Tier 3 spec). After a red commit, this one holds the code. Don't push yet.

A slice with no real logic (copy text, config, pure layout) gets no test. Say so and name the check that replaces it.

## When to stop

Work through ordinary trouble yourself. If the spec doesn't settle something, choose what fits its goal, add it to the spec's Decisions marked "(assumed during build)", and carry on. Stop the run and report only when:

- **The test looks wrong** once you start making it pass. Don't change it to get green, because a test its own author edited to pass proves nothing. Say what it should assert instead.
- **You're out of ideas**: the next attempt would repeat one you already tried. Say what you tried and what each attempt ruled out, then propose reverting to the last commit and trying a different approach, or splitting the slice smaller. Ask before discarding any work.
- **The work would contradict the spec** or touch something it lists as out of scope.

## Open the PR

Only where the work goes on a branch (see "Where the work lands"), when the spec's last slice or ticket is ticked and the checks pass, and before the review: push the branch (`git push -u origin <branch>`) and open a PR against the default branch, unless the branch already has one (a Projects thread's own PR): then update that PR's body. The PR body is what CI and the reviewer read, not a summary of the run:

- the spec's `Risk:` line, as written
- each done-when check: the command and the tail of its output, run just now
- how to undo it: revert the merge commit (`git revert -m 1 <merge commit>`), or close the PR and delete the branch before it merges

Never merge it yourself, whatever the risk; a session that merges would be grading its own work. How it merges is GitHub's job: see the review for low risk. After any fix in the review, push again.

## Review

When the spec's last slice or ticket is ticked and the checks pass, run the review before you report. It spawns a separate reviewer, which is worth it once per spec, so skip it when the run stopped early or left work open.

Pick the review by the spec's `Risk:` line (no line: normal). The line is the user's call, judged by the change and not by who wrote it, so never change it to get a lighter review:

- **low** (docs, copy, comments): read `../verify/SKILL.md` (the verify skill, next to this skill's folder) and follow its Auto section for this spec. Nobody is asked anything: end the report on the review log, not a question. If there is a PR, the repo allows auto-merge, and its default branch requires a status check (`gh api repos/{owner}/{repo}/rules/branches/<default branch>` has a `required_status_checks` rule, or `gh api repos/{owner}/{repo}/branches/<default branch>/protection` has `required_status_checks`), turn on auto-merge (`gh pr merge --auto --squash`), so GitHub merges it only once CI is green. Otherwise leave it for the user or the repo's own merge job.
- **normal**: read `../verify/SKILL.md` and follow it for this spec (not Auto). It ends by asking the user which findings to fix. With no findings, still end on a question: whether anything should change before it counts as done. At normal risk the user's answer is the sign-off, so never end without asking.
- **high**: as normal, and also run the built-in `/code-review` on the branch's diff (with the Skill tool; if you can't, tell the user to run it). Name the riskiest file and tell the user to read it themselves. An agent's review never counts as theirs.

## Report

One report at the end, for a reader who didn't watch the run:

- each slice: the behavior, the test and the assertion it failed on before the code existed, the checks that pass now, and the commit
- what you assumed where the spec was silent
- follow-ups you noticed but didn't do
- the PR link, if there is one. Outside a Projects thread (where Auto-fix is always on), say that turning on Auto-fix in the app's PR menu lets a session fix CI failures and review comments on it
- the review: the reviewer's counts and findings. For normal and high risk, end on the question: which ones to fix, or, with none, whether anything should change. If the run stopped early, the slice it stopped on and why.
