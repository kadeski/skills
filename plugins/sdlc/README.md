# sdlc

`sdlc` is a Claude Code plugin for building software with an agent without taking its word that the work is done. Nine skills cover the path from an idea to a reviewed change. The project's CI is what checks the work.

## Install

```
/plugin marketplace add kadeski/skills
/plugin install sdlc@kadeski
```

## Skills

Type a skill's name to run it, for example `/sdlc:spec`, or ask for it by name: Claude can load every skill but `weekly` on its own, so a Claude Code Projects thread, where nobody types slash commands, can run them. `pr-receipt` runs on its own whenever Claude writes a PR description, and `/sdlc:slice` runs the `verify` review when a spec is finished.

The skills assume nobody is there to answer, which is how a Projects thread or a headless run works: `slice`, `verify` and `lesson` decide by rule, and anything only you can decide comes back in the report as one decision with a recommended answer. Add `ask` to the arguments when you are in the session and want to be asked along the way. `grill` and `spec` are conversations, so run them where you can answer (in a project, the coordinator chat). GitHub calls go through `gh` locally and the GitHub MCP tools in a thread.

| Skill | What it does |
|---|---|
| `grill` | Questions you about a plan one decision at a time until nothing it depends on is left open. |
| `spec` | Writes the definition of done: goal, pass-or-fail checks, out of scope and thin vertical slices. Sets a risk level that decides how much review the build gets, and for high risk an `Undo:` line for what a revert cannot take back. |
| `slice` | Builds a spec test-first with nobody watching. Each slice gets a failing test shown as proof, the smallest code that passes it, the full checks and a commit. It lands the work the way the project's git rule says; with no rule, a solo repo with nothing gating main gets a push to main and anything else gets a PR. It keeps high-risk work on a branch until you sign off. |
| `verify` | Starts a reviewer that did not see the build. It runs the done-when checks itself, as the base commit defines them, and reads the diff against the spec, capped at 3 rounds. Each finding is fixed or rejected by rule. A change to the checks or review rules the work is judged by always goes to you. |
| `debug` | Reproduces a bug end to end, traces it to the layer that makes the wrong value, locks it with a failing test, then fixes it. |
| `lesson` | Turns a correction into a fix at the source: a test, a lint rule, a `REVIEW.md` or `CLAUDE.md` line, or a hook. Proves the fix catches the mistake. |
| `pr-receipt` | Lays out a PR description: a plain-language summary, then collapsed Proof (named tests, CI, logs) and Details sections. Claude uses it on its own whenever it writes or edits a PR description. |
| `evidence` | Ends a thread's or unattended run's final reply with a fixed block: the commit pushed, the CI result read back from GitHub, each check run and what was not checked, so a summary of the run carries proof. `slice` and `debug` end with it. |
| `weekly` | Finds code to delete, prunes `CLAUDE.md` and `REVIEW.md`, audits hooks and deny rules, and reads the track record (reviewer noise, reverts and follow-up fixes per risk level, or per kind of commit where work goes straight to main) to say which checkpoints have earned dropping. Reports first; a later run applies what you pick. |

## Checks

The plugin has no hook. A Claude Code Projects thread loads neither plugins nor repo settings, so a hook there checks nothing. Put the project's checks in CI and make them required on the default branch: that holds for every session, however it was started. An earlier stop-gate hook lives in this repo's history.

## Use in a Projects thread

Threads don't load plugins, but they do load the `.claude/skills/` folder of each repo they clone. `kadeski/skills` keeps symlinks there to every skill in this plugin and `doc-lint`, so adding `kadeski/skills` to a project's repositories makes the skills available in its threads, always matching `plugins/`.

## Version

The manifest has no `version` on purpose. Each commit then counts as a release, so an account that syncs the `kadeski/skills` marketplace picks up every push.

## License

MIT. See [LICENSE](LICENSE).
