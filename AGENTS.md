# AGENTS.md

The repo root is one plugin, `kadeski-skills`. Each skill is a folder `skills/<name>/SKILL.md`, and its user doc is `docs/<name>.md`. Every agent finds skills in `skills/` on its own, so adding a skill needs no manifest edit.

Each agent has its own manifest at the root:

- Claude Code: `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` (Grok Build reads these too)
- Codex: `plugin.json` and `.agents/plugins/marketplace.json`
- Cursor: `.cursor-plugin/plugin.json`
- Gemini CLI: `gemini-extension.json`

`name` and `version` must match in all four plugin manifests. Bump the version in all of them together.

Before committing, run `scripts/check.sh`.

Eval cases for a skill live in `evals/<skill>/`; see `evals/README.md`. `/hillclimb <skill>` improves a skill against them.

Writing style for skills and docs: simple terms, plain dashes (never em dashes), no filler.
