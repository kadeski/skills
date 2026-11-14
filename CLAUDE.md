# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`AGENTS.md` holds the marketplace layout, manifest rules and writing style. This file adds what it does not cover.

## Commands

- `scripts/check.sh` - run before every commit. Needs `jq` and the `claude` CLI. It checks that manifests agree on `name` and `version`, that each marketplace lists the right plugins (a plugin with only `.claude-plugin/plugin.json` is Claude-only and must be listed only in `.claude-plugin/marketplace.json`), that each `SKILL.md` `name` matches its folder, that no plugin file has a credential-like name (key, token, secret, password, auth) inside a `${...}` substitution, which the plugin directory holds under `MCP_FORWARDS_CREDENTIAL_ENV`, and runs `claude plugin validate --strict` on every plugin and the repo. The one warning it lets through is a plugin with no `version`. It also warns, without failing, when a plugin's tracked files differ from origin/main (as last fetched) but its version does not.
- `scripts/hooks/pre-commit` runs `scripts/check.sh` and blocks the commit if it fails. Turn it on once per clone with `git config core.hooksPath scripts/hooks` (this covers every worktree). It checks the working tree, so unstaged changes count too. `git commit --no-verify` skips it.
- Evals (see `evals/README.md`):
  - `evals/run.py dry <skill> -v` - grade untouched fixtures, no agent or judge, free.
  - `evals/run.py run <skill> --split train --case <glob> --runs 1` - one case.
  - `evals/run.py compare <old results> <new results>` - only compare runs made with the same `--model` and `--judge-model`.
- `/hillclimb <skill>` is a project skill in `.claude/skills/hillclimb/`.

## Archive

`archive/` holds retired plugins (`archive/tutor/`, replaced by `study` in kadeski/study). Nothing there ships or is listed in a marketplace, and `scripts/check.sh` skips it. Don't edit it; to bring a plugin back, move it to `plugins/` and list it again.

## The sdlc plugin

Claude-only, with no `version` on purpose (see `AGENTS.md`). Its tests are in `tests/sdlc/`:

- `stop-gate.sh` - the gate against scratch repos. No model run, free.
- The others are real headless model runs that cost money, so run them by hand. Each file's header says what it needs. `slice-pr.sh` opens a PR, and `next-auto.sh` files an issue, in `kadeski/sdlc-scratch`.

Skills read each other as files (`../verify/SKILL.md`), so keep them as siblings in `skills/`.

## Evals

- Never read `evals/<skill>/test/` or `evals/results/*/test/` while editing a skill, and never put case content into a skill.
- After changing cases or graders, make a new baseline; old scores no longer compare.
