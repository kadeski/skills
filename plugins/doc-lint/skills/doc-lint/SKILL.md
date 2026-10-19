---
name: doc-lint
description: "Audit a project's plan and design docs (PLAN.md, ROADMAP, docs/, ADRs, status tables) for broken links, stale numbers, contradictions between files, closed issues still listed as open, and open work with no issue, then report the findings without fixing them. Use when the user asks to lint, audit, health-check or tidy the docs or plan, or asks whether they are up to date. If the project has its own plan-lint style skill, use that instead."
---

Report only. Never edit a doc during the lint (saving the scope in step 0, on the user's yes, is the one exception); fix a finding only after the user approves it, and file an issue for any finding left unfixed (or draft one, when there is no tracker).

## 0. Scope

Work out which files are in scope before checking anything:

- **The docs.** Look for what CLAUDE.md, AGENTS.md or the README names as the plan or design docs. Otherwise take the usual places: `PLAN.md`, `ROADMAP.md`, `TODO.md`, `docs/`, `adr/` or `decisions/`, and any Markdown file with a status table. If it is still unclear, or the set is large, ask the user which files to cover.
- **History files.** Changelogs, run logs, retrospectives and write-ups of finished work record what was true at the time. Check their links, but skip them for staleness.
- **Saving the scope.** If you had to ask which files to cover, offer to save the answer so the next run doesn't ask again: a short `## Docs` section in CLAUDE.md (or AGENTS.md if the project uses that instead; create CLAUDE.md if neither exists) with a `Plan and design docs:` line and a `History files:` line. Write it only on a yes.
- **The project's own checks.** Look in `package.json` scripts, the Makefile, justfile, CI config and pre-commit hooks for doc checks: link checkers (`lychee`, `markdown-link-check`), `markdownlint`, generated-docs freshness (`docs:check`, `--check` flags), or scripts that print numbers the docs quote. Note the project's full check command (what CI runs) for use after fixes.
- **The issue tracker.** Note whether `gh` works here (`gh repo view`), and how the project's issues are labelled and written (read a few recent ones). If the project tracks work elsewhere (`glab`, or a Jira or Linear tool in this session), use that in place of `gh` throughout. If no tracker works here (no `gh`, not signed in, or a remote it can't read), the run has no tracker: steps 1 to 4 say what changes.

## 1. Mechanical checks

Run them from the repo root. Write the output to the scratchpad and read only the result lines.

- **The project's own doc checks** found in step 0, as they are.
- **Links**, if no checker covers them: every relative link and `#anchor` resolves, and every backticked path that looks like a repo path still exists. Write a short script in the scratchpad for this rather than checking by eye.
- **Issue state**: collect the issue numbers the docs list as open (in "Open issues" columns, "blocked on #N", to-do lists), and check their state with `gh issue view` or `gh issue list --state closed`. A closed issue still listed as open is a finding. With no tracker, skip this check.
- **Derived numbers**: when a command or script produces a number the docs quote (a total, a benchmark, a count, a version), run it and compare. Before calling a mismatch a finding, confirm both describe the same quantity under the same conditions. Run anything slow in the background.

## 2. Reading pass

Delegate the reading to read-only subagents such as `Explore`, one per area or group of files, each returning findings as `file:line` with a one-line quote. Read big files by section and grep them first; never load a very large file whole. Look for:

- **Contradictions.** The same fact, number, decision or status stated differently in two places. The newer, measured or more specific source wins; name both.
- **Stale facts.** A dated number ("as of", "read on", "measured") more than a week or so old that a command can re-read; a decision a later decision replaced; a status row or summary that no longer matches the section or file it summarizes.
- **Orphaned work.** Text that describes open work ("to do", "not yet", "TBD", "left to settle", "later") with no issue or ticket reference. With no tracker, skip this if the docs never cite an issue or ticket either.
- **Index drift.** A doc file, or a big new section, that the index, table of contents or section map doesn't list, or a size or count in the index that is far off.

## 3. Report

With no tracker, open with one line saying so and that issue state was not checked. Then list findings worst first, grouped as:

- **Wrong**: contradicts a measured or newer source.
- **Stale**: was true once, now out of date.
- **Missing**: open work without an issue, unlinked or unindexed files, broken links.

Each finding gets `file:line`, what is wrong, the source that shows it, and the fix in one line. End with the counts per group and ask which ones to fix.

## 4. Fixes (only after approval)

Make the approved fixes on a branch, then run the project's full check command from step 0. File an issue for every finding left unfixed, following the project's own issue conventions (labels, priority scheme, body template) as seen in step 0. If the project has none, give each issue a title naming the file and the problem, and a body with the finding's `file:line`, source and suggested fix. With no tracker, file nothing and don't add the findings to a plan doc; end with the unfixed findings written as issue drafts in that form, for the user to file.
