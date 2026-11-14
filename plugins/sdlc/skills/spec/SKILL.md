---
name: spec
description: Turn the current conversation or a feature request into a short spec file in the repo (goal, done-when checks, out of scope, thin vertical slices; for big changes also ordered tickets and one-paragraph ADRs) so the build can start in a fresh session. Use when the user types /spec or asks to write up, spec out, or define done for a feature before building it.
argument-hint: "[feature, or empty to use this conversation]"
disable-model-invocation: true
---

# spec

Write a spec for: $ARGUMENTS (empty means the feature we just discussed).

A spec is the written definition of done. A fresh session builds from it without stopping to ask, and /verify checks the result against it, so what it leaves out gets guessed. Keep it short enough to read in two minutes.

## 1. Check alignment

- The source is this conversation or the arguments above.
- If something only the user can decide is still open (who it's for, what done looks like, what's out of scope), ask now: one question at a time, with your recommended answer. Look up what the code can answer instead of asking.
- Don't invent requirements to fill gaps. Most bad output comes from misalignment, not bad code.

## 2. Size the change

Say the tier in one line, with the reason. Size it by how much is undecided and how far it reaches, not by how long it takes to build:

- **Tier 1, small fix** (one obvious change, nothing to decide): a spec is overhead. Say so and offer to just do it, with one rule: run the tests before claiming done. Stop here unless the user wants the spec anyway.
- **Tier 2, feature** (new behavior where "done" or "out of scope" could be read two ways): goal, done when, out of scope, slices.
- **Tier 3, big change** (several features' worth, or it changes how the system is built): Tier 2 plus ordered tickets, ADRs, and a branch or worktree.

Then propose a risk, which sets how much human review the build gets. Judge it by what the change could break, not by who will write it:

- **low**: docs, copy, comments. A wrong change costs a revert and nothing else. /slice reviews it with `/verify auto` and asks nobody.
- **normal**: most code. /slice runs `/verify` and the user picks which findings to fix.
- **high**: auth, payments, data migrations, deletes, anything hard to undo or that other people's work depends on. As normal, plus the built-in `/code-review`, and the user reads the riskiest file themselves.

## 3. Read just enough code

Find what the spec has to name for real: the test, lint and build commands, the closest existing work each slice can copy, and the files the change will touch. Don't describe the architecture. A fresh session can read the code itself.

## 4. Write the file

Save it where the project CLAUDE.md keeps specs, else `docs/specs/<short-slug>.md`:

```markdown
# <Feature name>

Tier: 2 · Status: draft · Risk: normal
<!-- Status: draft -> building -> done -->

## Goal
<1-3 sentences: what someone can do after this that they can't now, and why it matters>

## Done when
- [ ] `<command>` -> <expected result>
- [ ] <named test passes, or a named screen shows X>

## Out of scope
- <something a builder might add but shouldn't>

## Decisions
- <decision> - <why>

## Open questions
- none

## Slices
- [ ] 1. <behavior, end to end> - test: <what the failing test asserts> - copy: `<path of closest existing work>`
- [ ] 2. ...
```

For Tier 3, replace **Slices** with **Tickets**. One ticket is one piece of work with its own done check. /slice builds them in order and works out each ticket's slices when it starts:

```markdown
## Tickets
- [ ] T1 <title> - done when: <check> - after: none
- [ ] T2 <title> - done when: <check> - after: T1
```

Rules for the parts:

- **Done when**: every line comes back pass or fail: a command and its expected result, a named test passing, a named screen showing something. Never "works", "is fast" or "looks good". If you guessed a check, add "(guess - check this)".
- **Out of scope**: what a reasonable builder might add but shouldn't. This is what stops slice 3 from growing a settings page.
- **Slices**: thin and vertical. Each one is a behavior someone can see working end to end, not a layer ("add the table"). Order them so the app works after each one. Slice 1 is the thinnest end-to-end path. Each slice names its test, or, when there's no real logic, the check that replaces the test (a screenshot, a command and its output). /slice builds without stopping to show its tests, so the test line here is the user's one look at each test before it's written. Make it specific enough to disagree with: "rejects a 51st scheduled message with a 409", not "the limit works".
- **Decisions**: Tier 2 gets one line each. In Tier 3, a decision a future session might reopen gets an ADR: `docs/decisions/NNNN-slug.md`, one paragraph (context, decision, why, what we gave up), linked from here. Written decisions stop later sessions from relitigating them.
- **Open questions**: must say "none" before building. If not, ask them now.

## 5. Hand off

Reply with the path, the done-when list, the slice or ticket list and the proposed `Risk:` with its one-line reason, and ask for corrections. Ask the user to confirm the risk in so many words: it is their call, and it decides whether anyone reads the change before it merges. Once the user agrees:

1. Set `Status: building`, with the `Risk:` they confirmed.
2. Tier 3: suggest a branch or worktree (`claude -w <slug>`).
3. Tell the user to run `/clear`, then `/slice <path>` (`/sdlc:slice <path>` where the skills come from the `sdlc` plugin). It builds the whole spec and ends with the /verify review. A build that starts from the spec alone works from the same text /verify will check it against, so anything the spec is missing shows up early.
