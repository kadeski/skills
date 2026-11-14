---
name: next
description: Work through a plan that isn't a spec, such as an index or an issue tracker. Propose the next item as a continuation contract (item, done check, what runs after it, stop rule, scope, close-out), wait for one go, then run it and the items the contract lists after it. With `auto` after the item (an unattended run), post the contract on the issue and run it without waiting.
argument-hint: "[item, e.g. #45 or F30] [auto]"
disable-model-invocation: true
---

Resume the plan with a continuation contract. Arguments: $ARGUMENTS (the item, or empty to pick one). If `auto` follows the item, nobody is there to answer: read "Auto" at the end first.

## 1. Find the plan

- If the project CLAUDE.md names a plan, an index or an issue tracker, use that.
- If not, use open GitHub issues (`gh issue list`), by priority label and then by age.
- If the only plan is a spec in `docs/specs/`, say that /slice builds specs, and stop.
- If none of these exists, ask in one line where the plan is, and stop.

Read the index or issue list, not whole plan files. Open only the section for the chosen item.

## 2. Pick the item

- If an item was named above, use it.
- If not, take the top unblocked item: not done, and none of its dependencies open.
- If no item is clearly on top, list the top 3 with one reason each, ask which one, and stop.

## 3. Print the contract

```
Item: <name or ID> (<plan file and section, or issue link>)
Why this one: <one line>
Done when: <observable check>
Then: <the items to run after it, in order, or "stop">
Stop and report if: <N> min on one item, or a step fails with no untried idea left
Out of scope: anything else noticed goes in a follow-up list
Close-out: <as in CLAUDE.md, or the default below>

go, pick another, or adjust?
```

- **Done when** must be something the user can see in the reply: pasted command output, a booked run with its numbers, a PR link. Never "works" or "looks good". If the plan item carries its own acceptance check, use it. If not, propose one and add "(guess - check this)".
- **Then**: one go covers the whole run, so the user isn't asked again between items. List the items the user named, or the unblocked items that follow in the same milestone or index section, each with its done check. For an open-ended list such as an issue queue, write "stop".
- **Stop and report if**: the default is 90 min on one item, or a step that still fails when your next attempt would repeat an idea you already tried. A stop rule in the project CLAUDE.md replaces this default. You may propose a different time limit for this run, with a one-line reason.

## 4. Wait

End the turn after the question. Do no work until the user answers.

- **go**: continue to step 5.
- **pick another** or **adjust**: print the revised contract and wait again. If pick another names no item, take the next unblocked item, or list the top 3 if none is clearly on top.

## 5. Run

For the first item, then each item listed under Then:

- Record the start time with `date` before the first step. Check it again before each long step.
- Stop and report at once when the time limit is reached, or when a step fails and your next attempt would repeat an idea you already tried. Say what passed, what failed and what you would try next.
- Do only the items in the contract. Put anything else you notice in the follow-up list.
- If the item has real logic, build it test-first in thin slices, as the slice skill does: failing test shown as proof, then code, a commit per slice.

Close out each item before starting the next:

- If the project CLAUDE.md has a close-out rule, follow it.
- If not:
  1. Show the done-check evidence.
  2. Update the item's status in the plan.
  3. Commit locally. Do not push.

  Push or close issues only where CLAUDE.md says to.

If an item's done check fails, stop there and don't start the items after it. End the run with one report: each item with its evidence, then the follow-up list.

## Auto

`auto` in the arguments means an unattended run (a loop, a cloud routine, a headless `claude -p`): nobody reads the contract before the work starts, and nobody answers a question. Steps 1 to 5 hold, with these changes:

- **Pick (step 2)**: the item must be named. If it is missing, done or blocked, say so in one line and stop. Don't pick another.
- **Size it**: add a `Tier:` line to the contract under `Why this one`, with a one-line reason. Size by how much is undecided and how far the change reaches, not by how long it takes to build:
  - Tier 1: one obvious change with a one-line done check and nothing for the user to decide.
  - Tier 2: new behavior where "done" or "out of scope" could be read two ways.
  - Tier 3: several features' worth, or a change to how the system is built.

  Build only Tier 1. For Tier 2 or 3, post the contract, build nothing, and follow the project's rule for big work. With no such rule, report that the item needs /spec, and stop.
- **Contract (step 3)**: `Then:` is "stop", because an unattended run does one item. Leave out the "go, pick another, or adjust?" line. Post the contract as a comment on the item's issue, the way the project makes its GitHub calls, or where the project says a run's contract goes. An item with no issue gets its contract in the reply only.
- **Don't wait (step 4)**: skip it. Start step 5 in the same turn.
- **Run (step 5)**: if the item has real logic, read `../slice/SKILL.md` (the slice skill, next to this skill's folder) as a file and follow it, with the contract's `Done when` as its done-when check, so it doesn't ask for one. Skip its Review step: slice reviews only a finished spec, and the next bullet reviews the item. Don't call it through the Skill tool: slice is manual-only, and the call is blocked.
- **Review**: when the item's done check passes, and before its close-out, read `../verify/SKILL.md` as a file and follow its Auto section, with the contract's `Done when` as the checks. This holds for an item with no real logic too. Don't call it through the Skill tool. The review log goes where the project says; with no such rule, in a comment on the item's issue.
- **Lesson**: when the run made a mistake that would happen again in this project (the reviewer found the same class of thing twice, or a step failed on a wrong guess about the project), read `../lesson/SKILL.md` as a file and follow its Auto section. Commit the lesson as its own commit, alongside that round's fixes, and tell the next reviewer it is intended (in the prompt's "Already reported" line). With no further round, run the checks again as verify's "Fixes nobody reviews" says. Most runs have none.
- **Stopping**: never end the turn on a question. When a stop rule fires, report what passed, what failed and what you would try next the way the project says an unattended run reports (a park, a comment on the issue), then stop.
