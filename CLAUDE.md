# CLAUDE.md

`AGENTS.md` holds the marketplace layout, manifest rules and writing style. This file adds what it does not cover.

## Commands

- `scripts/check.sh` - run before every commit. Needs `jq` and the `claude` CLI. It checks that each manifest is valid and named for its folder, that the marketplace lists every plugin, that each `SKILL.md` `name` matches its folder, that the sdlc skills stay under their size budget (`budget=` in the script, lowered as skills are pruned), that no plugin file has a credential-like name (key, token, secret, password, auth) inside a `${...}` substitution, which the plugin directory holds under `MCP_FORWARDS_CREDENTIAL_ENV`, and runs `claude plugin validate --strict` on every plugin and the repo. The one warning it lets through is a plugin with no `version`. It also warns, without failing, when a plugin's tracked files differ from origin/main (as last fetched) but its version does not.
- `scripts/hooks/pre-commit` runs `scripts/check.sh` and blocks the commit if it fails. Turn it on once per clone with `git config core.hooksPath scripts/hooks` (this covers every worktree). It checks the working tree, so unstaged changes count too. `git commit --no-verify` skips it.
- Evals (see `evals/README.md`):
  - `evals/run.py dry <skill> -v` - grade untouched fixtures, no agent or judge, free.
  - `evals/run.py run <skill> --split train --case <glob> --runs 1` - one case.
  - `evals/run.py compare <old results> <new results>` - only compare runs made with the same `--model` and `--judge-model`.

## The sdlc plugin

Its tests in `tests/sdlc/` are real headless model runs that cost money, so run them by hand. Each file's header says what it needs. `slice-pr.sh` opens a PR in `kadeski/sdlc-scratch`.

`.claude/skills/` holds symlinks to every skill in `plugins/sdlc/skills/` and `plugins/doc-lint/skills/`, because Projects threads load a cloned repo's `.claude/skills/` but no plugins. A new skill gets a symlink too (`ln -s ../../plugins/<plugin>/skills/<name> .claude/skills/<name>`); `scripts/check.sh` fails when one is missing.

Skills read each other as files (`../verify/SKILL.md`), so keep them as siblings in `skills/`.

## Evals

- Never read `evals/<skill>/test/` or `evals/results/*/test/` while editing a skill, and never put case content into a skill.
