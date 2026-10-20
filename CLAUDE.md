# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`AGENTS.md` holds the marketplace layout, manifest rules and writing style. This file adds what it does not cover.

## Commands

- `scripts/check.sh` - run before every commit. Needs `jq` and the `claude` CLI. It checks that manifests agree on `name` and `version`, that each marketplace lists the right plugins (a plugin with only `.claude-plugin/plugin.json` is Claude-only and must be listed only in `.claude-plugin/marketplace.json`), that each `SKILL.md` `name` matches its folder, and runs `claude plugin validate --strict` on every plugin and the repo.
- Evals (see `evals/README.md`):
  - `evals/run.py dry <skill> -v` - grade untouched fixtures, no agent or judge, free.
  - `evals/run.py run <skill> --split train --case <glob> --runs 1` - one case.
  - `evals/run.py compare <old results> <new results>` - only compare runs made with the same `--model` and `--judge-model`.
- `/hillclimb <skill>` is a project skill in `.claude/skills/hillclimb/`.

## The tutor plugin

Claude-only. Three files ship in `plugins/tutor/skills/tutor/`:

- `SKILL.md` - what the agent does each run. Each goal is one claude.ai artifact titled `Tutor: <goal>`, and all state lives in that artifact's database (written with `ArtifactData`). The data model table in "The goal page" is the contract between the skill and the page.
- `tutor.js` - the fixed page runtime, published as a file next to each goal page. Its header comment is the full contract: slots, the classes it adds, what it reads and writes, and lock rules. The page itself is designed per goal and holds no lesson content.
- `look.css` - the fixed look, copied whole to the top of each goal page's `<style>`. Lesson pictures use its color names.

Rules that span these files:

- `tutor.js` has a `VERSION` constant. Bump it on every change to `tutor.js` or `look.css`, and also when the meaning of data the skill writes changes. Bump `goal/main.tutorJs` in `demo/tutor/seed.json` and in the `SKILL.md` example with it. The skill stores the version each page was published with in `goal/main.tutorJs`, republishes older pages, and refuses to touch a page newer than itself. A new `tutor.js` must keep working with documents written for older versions.
- A change to the data model touches the table in `SKILL.md`, the `DATA` section of the `tutor.js` header, and `demo/tutor/seed.json`.
- The plugin `version` in `.claude-plugin/plugin.json` is separate from `VERSION`; bump it on each release.

`demo/tutor/` is a test page for `tutor.js` (not shipped). Its README has the publish, seed and update steps.

## Evals

- Never read `evals/<skill>/test/` or `evals/results/*/test/` while editing a skill, and never put case content into a skill.
- After changing cases or graders, make a new baseline; old scores no longer compare.
- The tutor evals are paused until #52: the cases and `evals/tutor/lib.py` were written for the older file-based tutor (`goal.md`, lesson files, `head.html`) and do not match the artifact-based skill yet.
