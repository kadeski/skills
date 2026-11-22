# AGENTS.md

The repo is a marketplace, `kadeski`. Each plugin is a folder `plugins/<plugin>/` that ships on its own and is listed on its own in the Claude plugin directory. A plugin holds its skills in `skills/<name>/SKILL.md`, a `README.md` (its user doc and directory listing, at least 40 words) and a `LICENSE`. Keep anything that does not ship, such as evals, tests and scripts, out of `plugins/`: a plugin's tests live in `tests/<plugin>/`.

A plugin may live in its own repository instead: `study` is in kadeski/study, and its marketplace entry is a `url` source with that repository's `https://` address and its `release` branch. The directory follows a hook's Python script only at a repository root, which is why it moved. Use `url` with `https://` rather than a `github` source: `claude plugin update` clones a `github` source over SSH, which fails where github.com is not in `known_hosts`.

Each plugin has one manifest, `.claude-plugin/plugin.json`, and is listed in one marketplace, `.claude-plugin/marketplace.json`. The plugins ship for Claude Code only. A plugin may leave `version` out of its manifest (`sdlc` does): each commit then counts as a release, so accounts that sync the marketplace pick up every push.

To add a plugin, create its folder, add it to the marketplace and to the list in `README.md`.

Before committing, run `scripts/check.sh`.

Eval cases for a skill live in `evals/<skill>/`; see `evals/README.md`. `/hillclimb <skill>` improves a skill against them.

Writing style for skills and docs: simple terms, plain dashes (never em dashes), no filler.
