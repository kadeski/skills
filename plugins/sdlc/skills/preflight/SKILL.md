---
name: preflight
description: Check an agent run before it goes unattended (scheduled routines, /loop, headless `claude -p` in cron or CI, overnight or background agents, digests and monitors) against 5 questions (done, self-check, reach, stop, sign-off) and, for agents that read sources and post, 6 rules that make them fail loudly instead of quietly. Outputs a pass or missing checklist with the exact fix for each gap. Use before setting up or changing any agent that runs without someone watching.
argument-hint: "[the routine, script or prompt to check]"
disable-model-invocation: true
---

# preflight

Check: $ARGUMENTS

An unattended agent's main risk isn't a crash. It's failing quietly: it loses a source, runs on defaults, posts twice, or hits a spend cap and looks like a quiet day. Nobody notices for weeks.

## 0. Does it need to run unattended?

Often an agent started by hand during the day does the same job with someone watching. If that's true here, say so in one line, then continue either way.

## 1. Read the setup

The prompt, the schedule or cron line, CLI flags, settings and permissions, where it runs (local or cloud), what it reads, and what it writes or sends.

## 2. The 5 questions

For each, quote the concrete answer from the setup, or mark it MISSING with the fix:

1. **Done**: a goal, a spec, or a failing test to turn green.
2. **Self-check**: tests, a Stop hook, or a review step it has to pass. A stop-gate hook (`stop-gate.mjs`, run by a project setting or the `sdlc` plugin) with no command argument and no `.claude/checks.json` to run is MISSING: the gate stays silent without one, so it checks nothing. Fix: commit `.claude/checks.json` with the project's check commands.
3. **Reach**: permission rules, sandbox, worktree, the one branch it may push to. Read-only wherever it only reads. "Don't touch X" in the prompt isn't a control; use a deny rule or a sandbox.
   - **GitHub is the layer that holds everywhere** (local, cloud sessions, Projects threads), so read it: `gh api repos/{owner}/{repo}/rules/branches/<default branch>` for rulesets, and `gh api repos/{owner}/{repo}/branches/<default branch>/protection` for classic protection. The two layers add up, so judge them together. MISSING when neither requires a status check (no `required_status_checks` rule in the ruleset reply, and no `required_status_checks` in the protection reply, or no protection at all), or when neither blocks force pushes (no `non_fast_forward` rule, and classic protection absent or with `allow_force_pushes.enabled` true). Fix: a ruleset on the default branch that requires the CI check and blocks force pushes.
   - **Where the gate and the rules live**: a gate hook or a deny rule that lives only in `.claude/settings.local.json` or `~/.claude/settings.json` is MISSING for anything that runs in the cloud, which has neither. Fix: commit it to the repo's `.claude/settings.json` (`hooks/project-settings.example.json` in the `sdlc` plugin has the set). In a Projects thread repo settings don't load either; there only the `sdlc` plugin and GitHub reach.
4. **Stop**: `--max-turns`, `--max-budget-usd`, or a spend limit. Start at 3-5x a normal run's cost and tighten after a few runs. Hitting the cap must be reported, not look like a quiet run.
5. **Output and sign-off**: where the result lands (PR, summary, message) and who approves anything irreversible. Agent approval never stands in for a person's.

## 3. If it reads sources and reports (digest, monitor, triage)

Check the 6 rules:

1. Read from a bookmark per source (the newest item seen), not "the last 24 hours". A late run leaves a gap; an early run repeats.
2. A failed read isn't a quiet day. Keep that source's bookmark, report from the others, and end with "<source> unavailable this run".
3. Re-check each item live right before posting. Can't confirm it: drop it. State status plainly or leave the item out.
4. A post counts as sent only on confirmation; only then update the ledger and bookmarks. Unclear: mark it "maybe posted" and change nothing. Check that today's edition doesn't already exist.
5. Re-read preferences every run, from a store the agent can't edit. Can't read them: stop and say so. Never run on defaults.
6. Read-only access wherever it only reads, and a spend cap per run.

Also check:

- Preferences (the user's, read-only) are kept apart from state (bookmarks, ledger, run records).
- Items have stable IDs, so open ones carry over as one line ("still waiting, day 3").
- Dates are in the user's time zone, not the server's.
- Links are copied from source fields, never built by hand.
- A step that needs no judgment (open a PR, call an API) is plain code, not a tool the model has to pick.
- Text it reads can carry instructions. Ask what it could do if it obeyed them, and cut that down.

## 4. Output

A checklist table: check · status (pass, MISSING, n/a) · evidence or the exact fix (flag, permission rule, prompt line). Offer to apply the fixes. Close with: watch the first 3 runs before trusting it.
