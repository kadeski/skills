---
name: verify
description: Check that finished work meets its spec before calling it done. A fresh-context reviewer runs the done-when checks itself and reviews the diff against the spec for missing behavior, scope creep, stubs, wrong-layer fixes, weak tests and changes to the checks that judge it, with file:line evidence and a 3-round cap. By default (Auto) each finding is fixed or rejected by rule and nobody is asked; with `ask`, the user picks. Use when the user types /verify or asks "is it done?" or "check this against the spec". Not after every slice or commit, since it costs a separate reviewer; it runs once a whole spec or ticket is finished. For a general bug hunt on a diff with no spec, /code-review fits better.
argument-hint: "[spec path] [ask]"
---

# verify

Check the work against: $ARGUMENTS (a spec path; empty means the spec marked `Status: building`, or the done-when checks stated in this conversation).

**Who answers.** Nobody, by default. A Projects thread, a headless run or a loop has no one to read a question, so the review runs as Auto (the section at the end): read it first. With `ask` in the arguments, the user is in the session: follow steps 1 to 4 as written, where they confirm the checks and pick the findings to fix.

## 1. Gather (you, the author)

- **Spec**: the path. No spec: write the done-when checks from the conversation or ticket as a short list and confirm it with the user first.
- **Range**: from the commit before the work started (the parent of the first slice commit, or the merge-base with the main branch) to HEAD, plus uncommitted changes.
- **Policy files**: the files that decide how this work is judged: `.claude/settings.json`, `.claude/hooks/`, `REVIEW.md`, `CLAUDE.md` and `.github/workflows/`. List any the range changes (`git diff --stat <base> -- <those paths>`). The work can't loosen the rules it is judged by, so the reviewer judges it by the base versions of these files, and each change to them goes to the user.
- **Review log**: `<spec name>.review.md` next to the spec. If it exists, read the last round number, the last reviewed commit and the earlier findings.
- **Round 4 or later**: don't review again, and don't set `Status: done`. After 3 rounds a reviewer mostly finds old code and noise, or the approach itself is wrong: say so, and that the approach needs rethinking (with `ask`, step back with the user; else it is the report's one decision).

## 2. Spawn the reviewer

Use the Agent tool with `subagent_type: reviewer`, an agent that runs on the session's model: a reviewer should be at least as capable as the author it checks. If no `reviewer` agent is listed (a cloud session without it), use `general-purpose` and leave `model` unset. Fill in this prompt:

```
You are reviewing finished work against its spec. You did not write it. Do not edit any files.

Spec: <path>
Changes: `git diff <base>` (committed and uncommitted). Round <N>.
<Round 2 and later: review only `git diff <last reviewed commit>`. Earlier code was already reviewed.>
Project checks: <test, type, lint, build commands from CLAUDE.md as it was at <base> (`git show <base>:CLAUDE.md`)>
House rules: <`git show <base>:REVIEW.md`, or none>
Policy files changed in this work: <paths from step 1, or none>
Already reported, don't repeat: <earlier finding titles, or none>

1. Run every "Done when" check in the spec, and the project checks, yourself. For each: the command, the tail of its output, and pass, fail, or can't check (say why).
2. Read the diff against the spec. Look for:
   - spec behavior that's missing or only half there (stubs, TODOs, hard-coded values, happy path only)
   - behavior the spec didn't ask for, and anything listed under "Out of scope" that got touched
   - fixes in the wrong layer: patched where the symptom shows instead of where the wrong value is made
   - tests that check the wrong level, assert very little, or were edited to pass
   - each policy file changed in this work (listed above): a blocker, whatever it changes, with the diff as evidence and what it loosens or tightens. Judge the rest of the work by the base version, not the changed one.
3. For each finding: severity (blocker, should-fix, minor), file:line, evidence (quoted code or command output), why it matters, and a suggested fix. If one mistake shows up in several places, report it once as a class and list every instance.
4. Skip style, naming and formatting unless the house rules ask for them. Don't ask for defensive checks against cases that can't happen (trusted internal callers, already-validated input). A reviewer asked to find problems always finds something, and fixing every finding piles up needless code.
5. Start your reply with counts: "Done when: X/Y pass · blockers N · should-fix N · minor N". End with one line: what these checks prove, and what they don't.
```

## 3. Report to the user

- Show the reviewer's counts and findings as given. You may add a note to a finding ("intended: <reason>", "already fixed"), but don't drop or soften any.
- Each policy-file blocker is the user's call, not a fix you make: say what the change does and ask whether to keep it. The spec may name the change; it still goes to the user.
- Ask which findings to fix.

## 4. Log and loop

- Append to the review log: round N, date, commit reviewed, and each finding with its outcome once the user decides (fixed, won't fix: reason, or intended). Over time those outcomes show whether the reviewer is worth its noise.
- After the fixes, run /verify again for the next round (new diff only).
- When every done-when check passes and no blockers are left, set the spec's `Status: done`. Name what the user should still look at themselves: the riskiest file, and anything the checks can't prove.

## Auto

The default: nobody confirms a check list, picks which findings to fix or reads a question. Steps 1 to 4 hold, with these changes:

- **Gather (step 1)**: with no spec, the done-when checks are the ones the run was handed. Don't confirm them. The review log goes next to the spec; with no spec it goes where the project says a run's review goes (a section of the PR body, a comment on the item's issue), and with no such rule, in a comment on the item's issue.
- **Posting the log**: make GitHub calls the way this session makes them (`gh` locally, the GitHub MCP tools in a Projects thread). A comment or PR body is a change outside git, and a lost reply doesn't mean it wasn't made. Start the log with a marker line, `<!-- sdlc:verify <item or spec> -->`. Before posting, look for a comment or body that already holds the marker: if there is one, edit it to add this round, don't post a second. After posting, read it back. If a post fails with no clear answer (a timeout, a dropped connection), look for the marker before trying again.
- **Decide each finding by rule (step 3)**, without asking. Take the rules in this order and stop at the first that fits:
  0. A change to a policy file (step 1): **leave it open**, with no fix and no reject. Only a person can accept a change to the rules the work is judged by. See "Left open".
  1. The reviewer shows a done-when check or a project check (tests, types, lint, build) failing: **fix** it. It is a blocker, whatever it was filed as.
  2. The finding asks for a new feature, asks to change something out of scope, repeats a finding an earlier round rejected, or asks for a guard against a case that can't happen: **reject** it, with the reason in one line. A finding about the work itself (a stub, a hard-coded value, a weak or edited test, a fix in the wrong layer) is never rejected here: it goes to rule 3.
  3. A blocker or a should-fix: **fix** it, test-first where the fix has logic. One that comes back because its fix didn't work is fixed again, not rejected.
  4. A minor: **fix** it when it is a one-line change, else **reject** it as "minor, more than one line".

  Never drop a finding: each one is logged as fixed or rejected with its reason.
- **Log and loop (step 4)**: write each round to the log as `Review round <N>`, with the reviewer's counts line as given, then each finding with its outcome. If the round fixed a blocker or a should-fix, run the next round on the new diff only. If it fixed none (no findings, all rejected, or only one-line minors fixed), the review ends there.
- **Fixes nobody reviews**: after any fix that gets no further round (a one-line minor in the last round, or a round 3 fix), run the done-when checks and the project checks again yourself, and log their result.
- **The cap**: round 3 is the last review. If round 3 fixed a blocker or a should-fix, write "round 3 fixes not reviewed" in the log with each one.
- **Left open**: in any round, if a blocker or should-fix is one you could not fix, or a check still fails after your fix, don't call the work done and don't close the item out. The review ends at that round, even if the round fixed other findings. Report it the way the project says a run reports a stop (in a Projects thread, the thread's reply; else a comment on the issue), with the open findings and one decision for the user with your recommended answer. A policy-file change left open by rule 0 is reported the same way.
- **Done**: set a spec's `Status: done` when its checks pass and no blocker or should-fix is left open. Put the decisions you made that the spec didn't settle, and what the checks can't prove, in the log and the report, not in a question.
