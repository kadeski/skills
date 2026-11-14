---
name: lesson
description: Turn a correction into a fix at the source so the same mistake stops recurring in this project. Picks the lightest place that will reliably catch it (a test or type, a lint rule, REVIEW.md, a CLAUDE.md line, or a hook or deny rule for zero-exception rules), writes it, and proves it works. With `auto` (an unattended run), it picks the place and writes the fix without asking. Use when the user corrects a mistake that could happen again, says "this keeps happening", "don't do that again" or "fix this at the source", or the same review comment shows up twice.
argument-hint: "[the mistake, or empty for the last correction] [auto]"
disable-model-invocation: true
---

# lesson

Mistake: $ARGUMENTS (empty means the correction the user just made). If `auto` is among the arguments, nobody is there to answer: read "Auto" at the end first.

A correction in chat fixes one instance, and the next session starts without it. Put the fix where it keeps working. Pick the lightest place that will actually hold: every extra rule costs reading time, and every hook needs upkeep.

This is for things about this codebase. A personal preference about how to work with the user across all projects belongs in their global CLAUDE.md or memory instead.

## 1. Name it

One line each: what went wrong, what's right instead, and why. Ask only if the why isn't clear from the correction.

## 2. Pick the place

Go down this table and stop at the first row that fits:

| If the mistake... | Put the fix in | Because |
|---|---|---|
| could be caught by a test or type | a test, a type, an assertion | checkable beats remembered: it fails loudly every time |
| is a mechanical pattern (an import, a banned call, formatting) | a lint rule or formatter config | runs on every change for free |
| is something a reviewer should catch (what "broken" looks like here) | `REVIEW.md` | feeds /verify and /code-review |
| is a fact the agent couldn't get from the code, or wouldn't go look for | one `CLAUDE.md` line: "do Y, not X, because Z" | loads every session |
| must never happen, no exceptions, or already has a `CLAUDE.md` line that got missed again | a hook or deny rule (use the update-config skill; for "run the tests before finishing", the gate in `hooks/stop-gate` of the `sdlc` plugin, committed to the project as its README says, with the commands in `.claude/checks.json`) | the harness enforces it whatever the model decides |
| is a multi-step procedure that keeps going wrong | a skill | steps get followed, not reinvented |

Before adding a `CLAUDE.md` line: could the agent find this by reading the code, and would it actually go look? If both are yes, leave it out.

## 3. Check what's already there

Search `CLAUDE.md`, `REVIEW.md`, the lint config and `.claude/settings*.json` for a rule on this.

- **Exists and was ignored**: move it down the table (a `CLAUDE.md` line becomes a hook). Don't add emphasis. IMPORTANT and ALL CAPS mostly make the model over-apply a rule, and a line that keeps getting lost usually means the file is too long (suggest /weekly).
- **Contradicts another rule**: show both and ask which wins.

## 4. Write it and prove it

- Show the exact change (a diff or the new file) and apply it once the user agrees.
- Prove it bites: run the new test or lint rule against the bad version and show it fails. Trigger a new hook once and show it fire. A `CLAUDE.md` line can't be tested, so keep it to one line.
- Fix the instance that started this too, if it isn't fixed yet.

## Auto

`auto` in the arguments means an unattended run: the mistake is one the run itself hit (a review finding, a failed step, a wrong guess about the project), and nobody approves the fix. Steps 1 to 4 hold, with these changes:

- **Name it (step 1)**: if the why isn't clear, write your best reading and mark it "(guess)". Don't ask.
- **Pick the place (step 2)**: take the first row of the table that fits. A row that needs the user's own files (their global CLAUDE.md, their memory, a hook in their settings) is not open to an unattended run: use the next row that fits inside the project, and say in the report which row you would have picked. If no row fits inside the project, write nothing and report the mistake as a follow-up.
- **Check what's there (step 3)**: when the new rule contradicts an existing one, write neither. Report both as a follow-up; the run it is part of carries on.
- **Write it and prove it (step 4)**: apply the change without waiting for agreement, as its own commit in the run's change, and name it in the run's report. For a test, a type, a lint rule or a hook, prove it bites as step 4 says; if you can't show it failing on the bad version, don't keep it: revert it and report the mistake as a follow-up. A `REVIEW.md` or `CLAUDE.md` line can't be shown failing, so keep it to one line. A lesson that needs a new skill is not written by an unattended run: report it as a follow-up.
- One mistake, one fix. Don't write a lesson for something a check in the project already catches.
