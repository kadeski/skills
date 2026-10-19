# doc-lint

`doc-lint` is a Claude skill that audits a project's plan and design docs - `PLAN.md`, roadmaps, `docs/`, ADRs and status tables - and reports what is wrong without changing anything. It looks for broken links and paths, numbers the docs quote that no longer match what a command prints, facts stated differently in two files, issues listed as open that are closed, and open work with no issue. Fixes happen only after you approve them.

## Install

In Claude Code:

```
/plugin marketplace add kadeski/skills
/plugin install doc-lint@kadeski
```

## Usage

Ask Claude to lint, audit or health-check the docs, or whether the plan is up to date. In Claude Code you can also run `/doc-lint:doc-lint`.

- Claude works out which files are plan docs and which are history files (changelogs, run logs), which only get a link check. If it has to ask, it offers to save the answer in CLAUDE.md so later runs don't ask again.
- It runs the project's own doc checks, then reads the docs with subagents.
- It reports findings worst first, grouped as Wrong, Stale or Missing, each with `file:line`, the source that shows it and a one-line fix.
- You pick which to fix. Claude fixes those on a branch, runs the project's checks, and files an issue for each finding left unfixed. Without `gh` or another tracker, it writes issue drafts for you to file instead.

## License

MIT. See [LICENSE](LICENSE).
