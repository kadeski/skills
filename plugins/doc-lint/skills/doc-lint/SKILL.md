---
name: doc-lint
description: "Audit a project's plan and design docs (PLAN.md, ROADMAP, docs/, ADRs, status tables, plans split across files) for broken links, stale numbers, contradictions between files, statuses that disagree with where the work is tracked (issues, a TODO file or a main plan), and open work tracked nowhere, then report the findings without fixing them. Use when the user asks to lint, audit, health-check or tidy the docs or plan, or asks whether they are up to date. If the project has its own plan-lint style skill, use that instead."
---

Report only. Never edit a doc during the lint (saving the scope in step 0, on the user's yes, is the one exception); fix a finding only after the user approves it, and record findings left unfixed only where the user chooses.

## 0. Scope

Work out which files are in scope before checking anything:

- **The docs.** Look for what CLAUDE.md, AGENTS.md or the README names as the plan or design docs. Otherwise take the usual places: `PLAN.md`, `ROADMAP.md`, `TODO.md`, `docs/`, `adr/` or `decisions/`, per-phase or per-feature plan files that a main plan links to, and any Markdown file with a status table. If it is still unclear, or the set is large, ask the user which files to cover.
- **History files.** Changelogs, run logs, retrospectives and write-ups of finished work record what was true at the time. Check their links, but skip them for staleness.
- **Where open work is tracked.** Find the place the project keeps its list of open work, which every status in the docs should agree with. Use what CLAUDE.md, AGENTS.md or the README say; otherwise go by what the docs cite. Issue or ticket references (`#12`, `PROJ-34`) mean a tracker. Without them, it is a `TODO.md`, the checkboxes or status table in the plan, or a main plan that links to per-phase files. A project can use more than one, such as issues for bugs and a roadmap for features. If the docs point to no such place, there is none.
- **Saving the scope.** If you had to ask which files to cover or where open work is tracked, offer to save the answers so the next run doesn't ask again: a short `## Docs` section in CLAUDE.md (or AGENTS.md if the project uses that instead; create CLAUDE.md if neither exists) with a `Plan and design docs:` line, a `History files:` line and an `Open work:` line. Write it only on a yes. If a saved section has no `Open work:` line, work that part out as above; the missing line is not a finding.
- **The project's own checks.** Look in `package.json` scripts, the Makefile, justfile, CI config and pre-commit hooks for doc checks: link checkers (`lychee`, `markdown-link-check`), `markdownlint`, generated-docs freshness (`docs:check`, `--check` flags), or scripts that print numbers the docs quote. Note the project's full check command (what CI runs) for use after fixes.
- **The issue tracker.** Note whether `gh` works here (`gh repo view`), and how the project's issues are labelled and written (read a few recent ones). If the project tracks work elsewhere (`glab`, or a Jira or Linear tool in this session), use that in place of `gh` throughout. If no tracker works here (no `gh`, not signed in, a remote it can't read, or the project uses none), the run has no tracker: steps 1 to 4 say what changes.

## 1. Mechanical checks

Run them from the repo root. Write the output to the scratchpad and read only the result lines.

- **The project's own doc checks** found in step 0, as they are.
- **Links**, if no checker covers them: every relative link and `#anchor` resolves, and every backticked path that looks like a repo path still exists. Write a short script in the scratchpad for this rather than checking by eye.
- **Issue state**: collect the issue numbers the docs list as open (in "Open issues" columns, "blocked on #N", to-do lists), and check their state with `gh issue view` or `gh issue list --state closed`. A closed issue still listed as open is a finding. With no tracker, skip this check.
- **Derived numbers**: when a command or script produces a number the docs quote (a total, a benchmark, a count, a version), run it and compare. Before calling a mismatch a finding, confirm both describe the same quantity under the same conditions. Run anything slow in the background.

## 2. Reading pass

Delegate the reading to read-only subagents such as `Explore`, one per area or group of files, each returning findings as `file:line` with a one-line quote. Read big files by section and grep them first; never load a very large file whole. Look for:

- **Contradictions.** The same fact, number, decision or status stated differently in two places. The newer, measured or more specific source wins; name both.
- **Stale facts.** A dated number ("as of", "read on", "measured") more than a week or so old that a command can re-read; a decision a later decision replaced; a status row or summary that no longer matches the section or file it summarizes, including a main plan's status for a phase whose own plan file says otherwise.
- **Orphaned work.** Text that describes open work ("to do", "not yet", "TBD", "left to settle", "later") that isn't in the place where step 0 found open work is tracked: with issues, it has no issue or ticket reference; with a TODO file or main plan, that file doesn't list it (an item in that file is tracked by being there). Skip this check when step 0 found no such place.
- **Index drift.** A doc file, or a big new section, that the index, table of contents or section map doesn't list, or a size or count in the index that is far off.

## 3. Report

Open with one line saying where open work is tracked. With no tracker, that line also says so and that issue state was not checked. Then list findings worst first, grouped as:

- **Wrong**: contradicts a measured or newer source.
- **Stale**: was true once, now out of date.
- **Missing**: open work not in the place the project tracks it, unlinked or unindexed files, broken links.

Each finding gets `file:line`, what is wrong, the source that shows it, and the fix in one line. End with the counts per group, then ask which ones to fix and where the rest should go: the place the project tracks open work, or nowhere beyond this report. Leave out that second question when the `Open work:` line already says where. Draft nothing yet: issue drafts and other follow-up come in step 4, after the user answers.

## 4. Fixes (only after approval)

Make the approved fixes on a branch, then run the project's full check command from step 0. Then record the findings left unfixed where the user chose:

- **Issues**: one per finding, following the project's own issue conventions (labels, priority scheme, body template) as seen in step 0. If the project has none, give each issue a title naming the file and the problem, and a body with the finding's `file:line`, source and suggested fix. With no tracker, file nothing; end with the findings written as issue drafts in that form, for the user to file.
- **A TODO file or plan**: one item per finding in that file's own format, naming the file and the problem.
- **Nowhere**: leave them in the report.

If that choice isn't saved yet, offer to add it to the `Open work:` line so the next run doesn't ask.
