---
name: slice
description: Build a spec test-first without stopping for review, then have it reviewed. Each thin vertical slice gets a failing test shown as proof, the smallest code that passes it, the full checks, and a commit as a save point. A Tier 3 spec is built ticket by ticket the same way. When the spec is finished, the /verify review runs by itself. Use when the user types /slice, asks to build a spec, a ticket or the next slice, or wants something built test-first (TDD).
argument-hint: "[spec path] [slice or ticket] [ask]"
---

# slice

Build the open work in a spec, test-first. Arguments: $ARGUMENTS (all optional: the spec path, a slice or ticket number to build only that one, and `ask`).

**Who answers.** Nobody, by default. A Projects thread, a headless run or a loop has no one to read a question, so nothing here waits for an answer: a question only the user can decide goes in the report as one decision with your recommended default. With `ask` in the arguments, the user is in the session: stop and ask where this skill says so.

The run is hands-off. The user comes back to a built and reviewed spec with the evidence for each slice, so don't stop along the way to ask for a review. Two rules make that safe:

- The test exists and fails before the code does. When code and its test come out of one step, neither checks the other.
- Every slice ends in a commit: a save point to go back to.

## What to build

- **Spec**: the path given, else the spec marked `Status: building` in `docs/specs/` (or where CLAUDE.md keeps specs).
- **Slices** (Tier 2): every unticked slice in order, or only the one whose number was given.
- **Tickets** (Tier 3): every unticked ticket in order, or only the one named. When a ticket starts, split it into 2-4 thin vertical slices, write them under the ticket in the spec, and build them. When they're done, run the ticket's done-when check, show its output, and tick the ticket.
- **No spec**: build to the done-when check you were handed. With none, write a one-line done-when check yourself, mark it "(assumed)" and put it in the report (with `ask`: ask for one instead). Build without a spec only a small fix: one obvious change with nothing for the user to decide. Anything bigger, where "done" or "out of scope" could be read two ways, needs /spec first: report that and stop.

## Where the work lands

Decide once, before the first edit:

- **The project has a git rule** (project instructions or CLAUDE.md, such as "push straight to main"): follow it.
- **No rule, a solo repo, and an ungated default branch**: commit there, push at the end. Solo: only the user (and bots) committed in 90 days (`git log --since=90.days --format=%an | sort -u`). Ungated: `gh api repos/<owner>/<repo>/branches/<b>` shows `protected: false` and `.../rules/branches/<b>` has no `pull_request` or `required_status_checks` rule. A rejected push falls back to a PR.
- **No rule, a remote, anything else** (others commit, the branch is gated, or you can't tell): work on a branch and end in a PR. Use a non-default current branch, else `git switch -c <spec slug>`.
- **No remote**: commit on the current branch and don't push.
- **High risk** never lands on the default branch before the user signs off, whatever the rule: build on a branch and push that.

Before the first edit, read the code the work touches and the closest existing work the spec names, and follow its patterns. Run the project's checks once and note what already fails, so you neither blame a slice for those failures nor claim them as fixed.


## Each slice

1. **Write the failing test.** It asserts what the spec's slice line says, at the level that owns the behavior: a producer's job gets a producer test, not a check on the screen that displays it. Run it. It must fail on the assertion, not on an import error, a typo or a missing fixture. Show the test and its failing output as proof, then keep going. If the project asks for a red commit (its CLAUDE.md or rules say to commit the failing test before the code), commit the test now, with any empty stub it needs to fail on its assertion, as `<spec slug>: slice <N> red`.
2. **Make it pass** with the smallest code that does, without editing the test.
3. **Run the checks**: the new test, then the project's full checks (tests, types, lint, build, as CLAUDE.md lists them). Show each command and the tail of its output. "All tests pass" without output is not evidence.
4. **Save**: tick the slice in the spec and commit locally as `<spec slug>: slice <N> <behavior>` (with the ticket ID in front of `slice` in a Tier 3 spec). After a red commit, this one holds the code. Don't push yet.

A slice with no real logic (copy text, config, pure layout) gets no test. Say so and name the check that replaces it.

## When to stop

Work through ordinary trouble yourself. If the spec doesn't settle something, choose what fits its goal, add it to the spec's Decisions marked "(assumed during build)", and carry on. Stop the run and report only when:

- **The test looks wrong** once you start making it pass. Don't change it to get green, because a test its own author edited to pass proves nothing. Say what it should assert instead.
- **You're out of ideas**: the next attempt would repeat one you already tried. Say what you tried and what each attempt ruled out, then propose reverting to the last commit and trying a different approach, or splitting the slice smaller. Ask before discarding any work.
- **The work would contradict the spec** or touch something it lists as out of scope.
- **Green would need a change to the checks**: `.claude/settings.json`, `.claude/hooks/`, `REVIEW.md`, `CLAUDE.md` or `.github/workflows/`. Don't edit them to get past a failure: work that loosens the rules it is judged by proves nothing. Say what would change and why. A spec that asks for such a change can be built, and the review still puts it to the user.

## Push

When the spec's last slice or ticket is ticked and the checks pass, and before the review, push where "Where the work lands" says. Make GitHub calls with `gh` locally, the GitHub MCP tools in a thread. A push or PR call that fails with no clear answer (a timeout, a dropped connection) may still have worked: check (`git ls-remote origin <branch>`, or list the PRs for the branch) before trying again, so a retry doesn't push twice or open a second PR.

A PR (or the branch's existing one: update it) gets a body laid out with `../pr-receipt/SKILL.md`, holding:

- the spec's `Risk:` line, as written
- each done-when check: the command and the tail of its output, run just now
- how to undo: `git revert -m 1 <merge commit>`, or close the PR unmerged, plus the spec's `Undo:` line, if any, for effects outside git

Never merge a PR yourself; a session that merges would be grading its own work. After any fix in the review, push again.

## Review

When the spec's last slice or ticket is ticked and the checks pass, run the review before you report. It spawns a separate reviewer, so skip it when the run stopped early or left work open.

Read `../verify/SKILL.md` and follow it for this spec, in its default (auto) mode unless you have `ask`. Pick what else happens by the spec's `Risk:` line (no line: normal). The line is the user's call, judged by the change and not by who wrote it, so never change it to get a lighter review:

- **low** (docs, copy, comments) and **normal** (most code): the review decides each finding by rule and nobody is asked. The report carries the findings and what happened to each.
- **high**: also run the built-in `/code-review` on the diff (with the Skill tool; if you can't, say so in the report). The work stays on its branch. End the report with one decision for the user: merge it or not, naming the riskiest file for them to read first. An agent's review never counts as theirs.

## Report

One report at the end, for a reader who didn't watch the run:

- each slice: the behavior, the test and the assertion it failed on before the code existed, the checks that pass now, and the commit
- what you assumed where the spec was silent
- follow-ups you noticed but didn't do
- the review: the reviewer's counts and each finding with its outcome. If the run stopped early, the slice it stopped on and why
- at most one decision for the user, with your recommended answer: high-risk sign-off, a stop that needs them, or a check change the review left open

End with the block in `../evidence/SKILL.md`.
