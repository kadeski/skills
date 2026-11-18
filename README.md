# skills

Plugins for Claude Code by Kaden Staker, and the tooling that checks them: scored evals with a held-out test set, and one check over every manifest that runs before each commit and in CI.

```
/plugin marketplace add kadeski/skills
/plugin install <plugin>@kadeski
```

## Plugins

| Plugin | What it does |
|---|---|
| [sdlc](plugins/sdlc/README.md) | Ten skills for building with an agent, from questioning an idea to a reviewed change: spec, test-first build, separate-reviewer verify, debug, lessons, PR descriptions, report evidence. Built to run unattended, as in a Projects thread. |
| [study](https://github.com/kadeski/study) | Teaches one goal across sessions in the chat. It finds where your understanding ends, plans the shortest path, checks after each step and keeps a knowledge graph of what you were taught. Lives in its own repository. |
| [doc-lint](plugins/doc-lint/README.md) | Audits a project's plan and design docs for broken links, stale numbers, contradictions between files and open work tracked nowhere. Reports first and fixes only what you approve. |

All three are Claude Code only. Each README has the usage.

## How they are built

**Skills in Projects threads.** A Claude Code Projects thread loads no plugins, but it loads each cloned repo's `.claude/skills/`. Here those are symlinks to the skills in `plugins/`, so a project that lists this repo gets the same skills, never a stale copy.

**The checker is kept apart from the author.** In `sdlc`, the session that wrote the code never grades it. [verify](plugins/sdlc/skills/verify/SKILL.md) starts a reviewer that reads only the spec and the diff and runs the done-when checks itself. [slice](plugins/sdlc/skills/slice/SKILL.md) shows a failing test before any code exists, and never merges its own PR.

**Evals with a train and test split.** [evals/](evals/README.md) scores a skill on cases drawn from real use. Code checks what code can check, and a judge model rules on plain true-or-false claims for the rest. Scores come with a 95% band for run-to-run noise. `/hillclimb` changes a skill one edit at a time and keeps an edit only when both train and test rise beyond that band. The test cases are never read while editing.

**Headless end-to-end tests.** The scripts in [tests/sdlc/](tests/sdlc) run the skills for real in scratch repos with `claude -p`, then check the transcript, the git log and the PR the run left behind.

**One check before every commit, and on every push.** [scripts/check.sh](scripts/check.sh) runs as a pre-commit hook and in [CI](.github/workflows/check.yml). The marketplace must list every plugin, each skill's name must match its folder, and every plugin must pass `claude plugin validate --strict` (a plugin may leave out its version; nothing else is let through).

## Layout

```
plugins/<name>/     what ships: skills, README, LICENSE
.claude/skills/     symlinks to the shipped skills, for Projects threads
evals/              eval runner and cases per skill
tests/<name>/       tests for a plugin
scripts/check.sh    the pre-commit and CI check
archive/            retired plugins, not shipped or listed
```

[AGENTS.md](AGENTS.md) has the manifest and marketplace rules.

## License

MIT. See [LICENSE](LICENSE).
