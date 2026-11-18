---
name: weekly
description: Weekly hygiene pass on a repo worked on with agents. Finds what can be deleted or simplified across the whole codebase, prunes CLAUDE.md and REVIEW.md of lines that don't earn their place, audits hooks and deny rules (promote zero-exception rules, demote preferences), and reads the track record (reviewer noise, reverts and follow-up fixes per risk level) to say which checkpoints have earned dropping and which need adding back. Reports first and changes only what the user approves, in a later run. Use when the user types /weekly or asks for a cleanup, entropy or CLAUDE.md prune pass.
disable-model-invocation: true
---

# weekly

Report first and change nothing: the user picks later (in a Claude Code project, in the coordinator chat), and a separate run applies the picks.

## 1. Context

- `git log --since="1 week ago" --stat` (or since the last `weekly:` commit): where did most of the change land?
- Read `CLAUDE.md`, `REVIEW.md`, `.claude/settings.json` and `.claude/settings.local.json`.

## 2. Delete and simplify

Whole repo, starting with this week's hot spots (/simplify only covers changed code). Look for:

- dead code, unused exports, flags that are always on, old migration shims
- two helpers doing one job, abstractions with one caller, config nobody sets
- defensive checks on trusted internal input, try/catch blocks that swallow errors
- scaffolding built around an older model's limits (extra prompts, retries, wrappers).

For each hot spot, ask once: if we rebuilt this today, what would it look like at a tenth of the size?

List up to 10 candidates, ranked by lines removed per unit of risk. For each: what, where, why it exists, lines saved, risk, and how to check nothing broke. In a large repo, give the sweep to Explore subagents (`model: sonnet`), one per area, and judge their candidates yourself.

## 3. Prune CLAUDE.md

For each line:

- Could the agent find this by reading the code, and would it go look? Both yes: delete.
- Generic ("write clean code", "be careful"): delete.
- Outdated for current models: "think hard" (effort is the control now), IMPORTANT or ALL CAPS, architecture or file-layout descriptions, "use subagents to save context". Delete, or rewrite plainly.
- Guards against a problem the current model may no longer have: mark it "try deleting" and say how the user would notice if the problem came back. This includes "keep going" and "finish the whole task" lines. Some current models do end a turn with work left, so test before deleting those.
- Listed commands: run each one (or its `--help` if slow) to confirm it still works.
- A "never" or "always" that got missed anyway: promote it to a hook or deny rule.
- Exact rules stay even when the model "knows the idea": "ask the user", "and wait", a named command or key. Big models know concepts and still miss exact conditions and steps.
- Prune by measuring, not by reading. Where an eval or a test covers the line (or the skill: a repo of skills with evals in `evals/`), delete it on a branch and run them; keep the deletion only if the scores hold. Where nothing measures it, mark it "try deleting" as above, never delete it outright.

A correction line is a guess about one model: it fixed what that model got wrong, and the next model may not get it wrong. Check which model the sessions ran on (`/status`, or the model named in recent transcripts) against the one the last `weekly:` commit names. If it changed, or no weekly names one, say so first and tell the user to run `/doctor prompt-audit` on `CLAUDE.md` and the repo's skills, then apply or reject each finding (it needs a recent Claude Code: check `claude --version`). Name the model in this week's `weekly:` commit, so the next pass can compare.

What belongs: commands, project vocabulary, corrections ("you got X wrong, do Y"). Give `REVIEW.md` the same pass, and drop nits nobody acts on.

## 4. Audit hooks and deny rules

For each one: is it a zero-exception rule (keep) or a preference (demote to a `CLAUDE.md` line, or delete and let the model decide)? Has it misfired? Keep the enforced set small: every hook misfires sometimes and needs upkeep. `prompt` and `agent` hooks ask a model, so they aren't deterministic enforcement.

## 5. Track record

Checkpoints are dropped when the work has earned it, and added back when it hasn't. Read the evidence since the last `weekly:` commit (or the last 4 weeks the first time):

- **Reviewer noise**: the `*.review.md` logs next to the specs. Count each finding's outcome: fixed, won't fix, intended. A reviewer whose findings are mostly won't-fix or intended is noise: say which kinds, and suggest a `REVIEW.md` line that drops them. Also count rounds to pass per spec.
- **Regret-free landings**: the units landed on the default branch in the period: a merged PR, or the direct commits naming one spec (`<slug>: slice <N>`), each with its `Risk:`; any other direct commit, grouped by message prefix (`ingest:`, `edit:`) or top folder. Skip merges and commits a tool made (backups, bot bumps). A unit regrets when it needed a revert (`git log --grep '^Revert'`) or a follow-up fix within a week: a later commit naming it, or correcting lines it added (not building on them). Read each candidate's diff (`git log <sha>.. --until=<+7 days> -- <its files>`): a shared file (an index, a log) is not enough. A backup commit can be the fix: hand edits arrive that way. Give the rate per risk level and kind, with the count, and name each regret.
- **What it says**: a risk level or kind with no regrets over 10 or more units has earned dropping one checkpoint, such as high-risk work skipping the extra `/code-review` pass. Propose one, name the evidence, and never apply it yourself: the user decides. A regret nobody read before it landed (low risk, a direct commit): propose adding a checkpoint back for that kind of change. Fewer than 10 units: too little to judge.

## 6. Report and apply

- One table per section: item · where · action (delete, simplify, move, promote, demote) · why · risk. Number the items so the user can pick by number. End the run there.
- When a later run is handed the picks: apply them one commit each (`weekly: <what>`), running the project checks after each. Revert any that break them.
- Finish with: lines removed, rules removed and added, anything skipped.
- Last line: suggest one small real task from this week's work for the user to do without an agent, so the skills they're delegating don't quietly fade.
