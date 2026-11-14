---
name: weekly
description: Weekly hygiene pass on a repo worked on with agents. Finds what can be deleted or simplified across the whole codebase, prunes CLAUDE.md and REVIEW.md of lines that don't earn their place, and audits hooks and deny rules (promote zero-exception rules, demote preferences). Reports first and changes only what the user approves. Use when the user types /weekly or asks for a cleanup, entropy or CLAUDE.md prune pass.
disable-model-invocation: true
---

# weekly

Agents speed up entropy. They add code readily and almost never suggest that 100k lines could be 10k. Instructions written for last month's model turn into constraints for this one. Schedule the cleanup or it never happens.

Report first. Change nothing until the user picks what to apply.

## 1. Context

- `git log --since="1 week ago" --stat` (or since the last `weekly:` commit): where did most of the change land? Entropy collects there.
- Read `CLAUDE.md`, `REVIEW.md`, `.claude/settings.json` and `.claude/settings.local.json`.

## 2. Delete and simplify

Whole repo, starting with this week's hot spots (/simplify only covers changed code). Look for:

- dead code, unused exports, flags that are always on, old migration shims
- two helpers doing one job, abstractions with one caller, config nobody sets
- defensive checks on trusted internal input, try/catch blocks that swallow errors
- scaffolding built around an older model's limits (extra prompts, retries, wrappers). Ask: what's the actual reason to keep this?
- files that grew a lot this week

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

A correction line is a guess about one model: it fixed what that model got wrong, and the next model may not get it wrong. Check which model the sessions ran on (`/status`, or the model named in recent transcripts) against the one the last `weekly:` commit names. If it changed, or no weekly names one, say so first and tell the user to run `/doctor prompt-audit` on `CLAUDE.md` and the repo's skills, then apply or reject each finding (it needs a recent Claude Code: check `claude --version`). Name the model in this week's `weekly:` commit, so the next pass can compare.

What belongs: commands, project vocabulary, corrections ("you got X wrong, do Y"). Give `REVIEW.md` the same pass, and drop nits nobody acts on.

## 4. Audit hooks and deny rules

For each one: is it a zero-exception rule (keep) or a preference (demote to a `CLAUDE.md` line, or delete and let the model decide)? Has it misfired? Keep the enforced set small: every hook misfires sometimes and needs upkeep. `prompt` and `agent` hooks ask a model, so they aren't deterministic enforcement.

## 5. Report and apply

- One table per section: item · where · action (delete, simplify, move, promote, demote) · why · risk. Then ask which to apply.
- Apply approved items one commit each (`weekly: <what>`), running the project checks after each. Revert any that break them.
- Finish with: lines removed, rules removed and added, anything skipped.
- Last line: suggest one small real task from this week's work for the user to do without an agent, so the skills they're delegating don't quietly fade.
