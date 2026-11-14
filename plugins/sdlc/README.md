# sdlc

`sdlc` is a Claude Code plugin for building software with an agent without taking its word that the work is done. Nine skills cover the path from an idea to a reviewed change, and a hook refuses to let Claude finish a turn while the project's checks fail.

## Install

```
/plugin marketplace add kadeski/skills
/plugin install sdlc@kadeski
```

## Skills

Type a skill's name to run it, for example `/sdlc:spec`, or ask for it by name: Claude can load every skill but `weekly` and `preflight` on its own, so a Claude Code Projects thread, where nobody types slash commands, can run them. `pr-receipt` runs on its own whenever Claude writes a PR description, and `/sdlc:slice` runs the `verify` review when a spec is finished.

The skills assume nobody is there to answer, which is how a Projects thread or a headless run works: `slice`, `verify` and `lesson` decide by rule, and anything only you can decide comes back in the report as one decision with a recommended answer. Add `ask` to the arguments when you are in the session and want to be asked along the way. `grill` and `spec` are conversations, so run them where you can answer (in a project, the coordinator chat). GitHub calls go through `gh` locally and the GitHub MCP tools in a thread.

| Skill | What it does |
|---|---|
| `grill` | Questions you about a plan one decision at a time until nothing it depends on is left open. |
| `spec` | Writes the definition of done: goal, pass-or-fail checks, out of scope and thin vertical slices. Sets a risk level that decides how much review the build gets, and for high risk an `Undo:` line for what a revert cannot take back. |
| `slice` | Builds a spec test-first with nobody watching. Each slice gets a failing test shown as proof, the smallest code that passes it, the full checks and a commit. It lands the work the way the project's git rule says, and keeps high-risk work on a branch until you sign off. |
| `verify` | Starts a reviewer that did not see the build. It runs the done-when checks itself, as the base commit defines them, and reads the diff against the spec, capped at 3 rounds. Each finding is fixed or rejected by rule. A change to the checks or review rules the work is judged by always goes to you. |
| `debug` | Reproduces a bug end to end, traces it to the layer that makes the wrong value, locks it with a failing test, then fixes it. |
| `lesson` | Turns a correction into a fix at the source: a test, a lint rule, a `REVIEW.md` or `CLAUDE.md` line, or a hook. Proves the fix catches the mistake. |
| `preflight` | Checks an agent run before it goes unattended: what done means, how it checks itself, what it can reach, when it stops, who signs off, and how it avoids repeating or gets back from what it changes outside git. |
| `pr-receipt` | Lays out a PR description: a plain-language summary, then collapsed Proof (named tests, CI, logs) and Details sections. Claude uses it on its own whenever it writes or edits a PR description. |
| `weekly` | Finds code to delete, prunes `CLAUDE.md` and `REVIEW.md`, audits hooks and deny rules, and reads the track record (reviewer noise, reverts and follow-up fixes per risk level) to say which checkpoints have earned dropping. Reports first; a later run applies what you pick. |

## The gate

`hooks/stop-gate/stop-gate.mjs` runs on `Stop` and `TaskCompleted`. Commit your check commands as `.claude/checks.json`:

```json
{
  "stop": "npm run typecheck && npm test",
  "task": "npm test"
}
```

- While `stop` fails, Claude is sent back to work with the last 60 lines of output.
- While `task` fails, a task cannot be ticked. `slice` makes one task per slice, so each slice is checked by the project and not only by the agent.
- After 3 tries it lets the turn end and warns you.
- With `"requires": "node_modules"` (any path relative to the checkout root), a checkout without that path is skipped, so a fresh worktree with no dependencies installed isn't blocked.
- An unchanged tree is not checked twice, and a repo with no `.claude/checks.json` is left alone, so the plugin is safe to enable everywhere.

[hooks/stop-gate/README.md](hooks/stop-gate/README.md) has the details. To commit the gate to a repo without the plugin, copy the script and merge [hooks/project-settings.example.json](hooks/project-settings.example.json), which also holds deny rules for force pushes and ask rules for commands that discard work. Do not do both in one repo, or the gate runs twice.

## Version

The manifest has no `version` on purpose. Each commit then counts as a release, so an account that syncs the `kadeski/skills` marketplace picks up every push.

## License

MIT. See [LICENSE](LICENSE).
