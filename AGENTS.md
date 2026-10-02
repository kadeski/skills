# AGENTS.md

The repo is a marketplace, `kadeski`. Each plugin is a folder `plugins/<plugin>/` that ships on its own and is listed on its own in the Claude plugin directory. A plugin holds its skills in `skills/<name>/SKILL.md`, a `README.md` (its user doc and directory listing, at least 40 words) and a `LICENSE`. Keep anything that does not ship, such as evals and scripts, out of `plugins/`.

Each plugin has a manifest per agent:

- Claude Code: `.claude-plugin/plugin.json` (Grok Build reads it too)
- Codex: `plugin.json`
- Cursor: `.cursor-plugin/plugin.json`

`name` and `version` must match in all three. Bump the version in all of them together. Gemini CLI has no plugin manifest: users install a skill with `gemini skills install <repo url> --path plugins/<plugin>/skills/<name>`.

Each plugin is listed in every marketplace at the root:

- Claude Code: `.claude-plugin/marketplace.json` (Grok Build and `npx skills` read it too)
- Codex: `.agents/plugins/marketplace.json`
- Cursor: `.cursor-plugin/marketplace.json`

To add a plugin, create its folder, add it to all three marketplaces and to the list in `README.md`.

Before committing, run `scripts/check.sh`.

Eval cases for a skill live in `evals/<skill>/`; see `evals/README.md`. `/hillclimb <skill>` improves a skill against them.

Writing style for skills and docs: simple terms, plain dashes (never em dashes), no filler.
