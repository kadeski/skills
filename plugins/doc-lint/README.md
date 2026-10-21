# doc-lint

`doc-lint` is a Claude skill that audits a project's plan and design docs - `PLAN.md`, roadmaps, `docs/`, ADRs, status tables and plans split across files - and reports what is wrong without changing anything. It looks for broken links and paths, numbers the docs quote that no longer match what a command prints, facts stated differently in two files, statuses that disagree with where the work is tracked, and open work that isn't tracked anywhere. It works with however the project tracks work: GitHub issues (or GitLab, Jira or Linear), a `TODO.md`, or a main plan that links to per-phase files. Fixes happen only after you approve them.

## Install

In Claude Code:

```
/plugin marketplace add kadeski/skills
/plugin install doc-lint@kadeski
```

## Usage

Ask Claude to lint, audit or health-check the docs, or whether the plan is up to date. In Claude Code you can also run `/doc-lint:doc-lint`.

- Claude works out which files are plan docs, which are history files (changelogs, run logs) that only get a link check, and where open work is tracked. If it has to ask, it offers to save the answers in CLAUDE.md so later runs don't ask again.
- It runs the project's own doc checks, then reads the docs with subagents. It also runs `gh` (or your tracker's tool) to read issue state, and short scripts it writes to a scratch folder to check links.
- It reports findings worst first, grouped as Wrong, Stale or Missing, each with `file:line`, the source that shows it and a one-line fix.
- You pick which to fix and where the rest go: your tracker, your TODO file or plan, or nowhere. Claude fixes the chosen ones on a branch, runs the project's checks, and records the rest where you said. If you pick issues and no tracker works here, it writes issue drafts for you to file instead.

## License

MIT. See [LICENSE](LICENSE).
