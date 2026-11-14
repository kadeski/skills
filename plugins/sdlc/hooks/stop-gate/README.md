# stop-gate

Enforces the one Tier 1 rule, "run the tests before claiming done", as a hook instead of a `CLAUDE.md` line. A hook runs every time; a `CLAUDE.md` line is a guideline the model may skip.

One script answers two events:

- `Stop`, at the end of each Claude turn: runs the full checks.
- `TaskCompleted`, when a task is ticked (`/slice` makes one task per slice): runs the narrower task checks, so a slice can't be ticked while its area fails.

What it does on each:

- no check command (no argument and no `.claude/checks.json`) -> nothing, so the gate is safe to load everywhere
- tree unchanged since this check's last green run -> nothing (chat turns stay fast)
- checks pass -> remembers this tree as green for that check command. Each command keeps its own green tree, so a green task run never skips the full run at the end
- checks fail -> sends Claude back to work with the last 60 lines of output (`Stop`: JSON `decision: "block"`; `TaskCompleted`: exit 2 with the tail on stderr)
- still failing after 3 tries in one turn of a session, or 3 refusals of one task -> lets it through, warns you, and stays quiet for that check until files change. Each session keeps its own count, so two sessions in one checkout both reach the give-up
- not a git repo -> nothing

On both events it checks the checkout the session started in, and also every other checkout of the same repo (a worktree elsewhere) that the session edited with Edit, Write, MultiEdit or NotebookEdit. It finds those edits in the session's transcript and its subagents' transcripts. Edits made through Bash are not seen. Each checkout runs its own `.claude/checks.json`, and the checks run one after another, so keep their total under the hook's timeout.

State lives in each checkout's git dir as `claude-stop-gate.json` (never committed).

## The checks file

Commit the project's check commands as `.claude/checks.json`:

```json
{
  "stop": "npm run typecheck && npm test",
  "task": "npm test"
}
```

`stop` is required; `task` is optional and falls back to `stop`. A command-line argument (`stop-gate.mjs "npm test"`) wins over the file on both events. The command runs through `cmd.exe` on Windows, so use syntax that works there.

## Turn it on for a project

Commit it with the repo, so local and plain cloud sessions both get it (a cloud session has no `~/.claude`, so a hook pointing there does nothing):

1. Copy `stop-gate.mjs` to the repo's `.claude/hooks/stop-gate.mjs`.
2. Merge `../project-settings.example.json` into the repo's `.claude/settings.json`. It holds the `Stop` and `TaskCompleted` hooks, the force-push deny rules and the ask rules for commands that discard uncommitted work, for both the Bash and the PowerShell tool. It also sets `CLAUDE_CODE_ENABLE_TODO_TOOLS=1`: current models get no task tools without it, and with no tasks `TaskCompleted` never fires.
3. Write `.claude/checks.json`.

`bash tests/sdlc/deny-rules.sh` (from the root of kadeski/skills) checks the rules in a headless run.

In a Claude Code Projects thread, repo settings don't load. There the `sdlc` plugin brings the same gate (it reads the same `.claude/checks.json`), and CI is the check that holds regardless; see the plugin README. Don't enable the plugin in a repo that also vendors the gate: both copies would run.

Optional env vars: `STOP_GATE_MAX_BLOCKS` (default 3), `STOP_GATE_TIMEOUT_SEC` (default 540), and `STOP_GATE_REQUIRES`, a path relative to the checkout root that must exist before the gate runs there. Set it to `node_modules`, for example, so a fresh worktree with no dependencies installed is skipped instead of blocked 3 times.

Turn it off: delete the hook entries, or run `/hooks` to see what's active.

## Test

`bash tests/sdlc/stop-gate.sh` (from the root of kadeski/skills) runs it against scratch repos: fail -> block, pass -> green, unchanged -> skip, changed -> rerun, cap -> warn, then quiet; and for `TaskCompleted` and the checks file: exit 2 with the tail on stderr, a green task check doesn't skip the stop check, 3 refusals per task, no checks file -> nothing; two sessions each reaching the give-up; `STOP_GATE_REQUIRES`; and edited worktrees elsewhere, from the main and a subagent transcript, but not another repo.
