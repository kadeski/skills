# skills

Plugins for Claude Code by Kaden Staker, and the tooling that checks them: scored evals with a held-out test set, a hook that blocks "done" while checks fail, and a pre-commit check over every manifest.

```
/plugin marketplace add kadeski/skills
/plugin install <plugin>@kadeski
```

## Plugins

| Plugin | What it does |
|---|---|
| [sdlc](plugins/sdlc/README.md) | Nine skills for building with an agent, from questioning an idea to a reviewed change: spec, test-first build, separate-reviewer verify, debug, lessons. A hook refuses a finished turn or a ticked task while the repo's checks fail. |
| [tutor](plugins/tutor/README.md) | Teaches one goal at a time on one claude.ai page per goal. You answer on the page, Done sends your answers to be graded, and the rules you pass come back as spaced review. |
| [study](https://github.com/kadeski/study) | Teaches one goal across sessions in the chat. It finds where your understanding ends, plans the shortest path, checks after each step and keeps a knowledge graph of what you were taught. Lives in its own repository. |
| [doc-lint](plugins/doc-lint/README.md) | Audits a project's plan and design docs for broken links, stale numbers, contradictions between files and open work tracked nowhere. Reports first and fixes only what you approve. |

All four are Claude Code only. Each README has the usage.

## How they are built

**A gate the model cannot skip.** A line in `CLAUDE.md` that says "run the tests before finishing" is a suggestion. [stop-gate.mjs](plugins/sdlc/hooks/stop-gate/stop-gate.mjs) is a hook: it runs the project's checks when Claude tries to end a turn or tick a task, and sends it back to work with the failing output. It skips an unchanged tree, gives up after 3 tries with a warning, and does nothing in a repo that has not opted in. [59 cases](tests/sdlc/stop-gate.sh) cover it with no model run.

**The checker is kept apart from the author.** In `sdlc`, the session that wrote the code never grades it. [verify](plugins/sdlc/skills/verify/SKILL.md) starts a reviewer that reads only the spec and the diff and runs the done-when checks itself. [slice](plugins/sdlc/skills/slice/SKILL.md) shows a failing test before any code exists, and never merges its own PR.

**Evals with a train and test split.** [evals/](evals/README.md) scores a skill on cases drawn from real use. Code checks what code can check, and a judge model rules on plain true-or-false claims for the rest. Scores come with a 95% band for run-to-run noise. `/hillclimb` changes a skill one edit at a time and keeps an edit only when both train and test rise beyond that band. The test cases are never read while editing.

**A page runtime with a versioned contract.** Each `tutor` goal is a claude.ai page whose state lives in the page's database. [tutor.js](plugins/tutor/skills/tutor/tutor.js) is the fixed runtime every page shares; the skill records the version each page was published with, republishes older pages and refuses to touch a newer one.

**Headless end-to-end tests.** The scripts in [tests/sdlc/](tests/sdlc) run the skills for real in scratch repos with `claude -p`, then check the transcript, the git log and the PR or issue the run left behind.

**One check before every commit.** [scripts/check.sh](scripts/check.sh) runs as a pre-commit hook. Manifests must agree, each marketplace must list the right plugins, each skill's name must match its folder, and every plugin must pass `claude plugin validate --strict` (a plugin may leave out its version; nothing else is let through).

## Layout

```
plugins/<name>/     what ships: skills, hooks, README, LICENSE
evals/              eval runner and cases per skill
tests/<name>/       tests for a plugin
scripts/check.sh    the pre-commit check
demo/tutor/         a test page for tutor.js
```

[AGENTS.md](AGENTS.md) has the manifest and marketplace rules.

## License

MIT. See [LICENSE](LICENSE).
