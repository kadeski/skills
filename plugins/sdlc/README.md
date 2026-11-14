# sdlc

`sdlc` is a Claude Code plugin for building software with an agent without taking its word that the work is done. Nine skills cover the path from an idea to a reviewed change, and a hook refuses to let Claude finish a turn while the project's checks fail.

## Install

```
/plugin marketplace add kadeski/skills
/plugin install sdlc@kadeski
```

## Skills

Every skill is manual: type its name, for example `/sdlc:spec`. None runs on its own, apart from two hand-offs: `/sdlc:slice` runs the `verify` review when a spec is finished, and `/sdlc:next <item> auto` follows `slice`, `verify` and `lesson`.

| Skill | What it does |
|---|---|
| `grill` | Questions you about a plan one decision at a time until nothing it depends on is left open. |
| `spec` | Writes the definition of done: goal, pass-or-fail checks, out of scope and thin vertical slices. Sets a risk level that decides how much review the build gets. |
| `slice` | Builds a spec test-first with nobody watching. Each slice gets a failing test shown as proof, the smallest code that passes it, the full checks and a commit. |
| `verify` | Starts a reviewer that did not see the build. It runs the done-when checks itself and reads the diff against the spec, capped at 3 rounds. |
| `debug` | Reproduces a bug end to end, traces it to the layer that makes the wrong value, locks it with a failing test, then fixes it. |
| `lesson` | Turns a correction into a fix at the source: a test, a lint rule, a `REVIEW.md` or `CLAUDE.md` line, or a hook. Proves the fix catches the mistake. |
| `next` | Works through a plan that is not a spec, such as an issue queue, one contract at a time. With `auto` it runs unattended and decides each review finding by rule. |
| `preflight` | Checks an agent run before it goes unattended: what done means, how it checks itself, what it can reach, when it stops and who signs off. |
| `weekly` | Finds code to delete, prunes `CLAUDE.md` and `REVIEW.md`, and audits hooks and deny rules. Reports first and changes only what you approve. |

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
- An unchanged tree is not checked twice, and a repo with no `.claude/checks.json` is left alone, so the plugin is safe to enable everywhere.

[hooks/stop-gate/README.md](hooks/stop-gate/README.md) has the details. To commit the gate to a repo without the plugin, copy the script and merge [hooks/project-settings.example.json](hooks/project-settings.example.json), which also holds deny rules for force pushes and ask rules for commands that discard work. Do not do both in one repo, or the gate runs twice.

## Version

The manifest has no `version` on purpose. Each commit then counts as a release, so an account that syncs the `kadeski/skills` marketplace picks up every push.

## License

MIT. See [LICENSE](LICENSE).
