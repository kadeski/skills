# Practice method

Practice trains one thing: an idea the learner was taught comes to mind when nothing names it. Every rule below serves that.

A **target** is a proposition (`p_` id) or a chain (`c_` id) from the graph. A **moment** is a point in a problem where the learner has to find an idea on their own. A recall problem has one moment; a composition problem has one per idea in the chain.

## Modes

Each target goes through three modes, in this order:

1. **recall** - the problem's cue is new or weak. The learner has to bring the idea to mind. The target is one proposition.
2. **discrimination** - the problem fits a similar wrong idea (the lure) on the surface, but only the right idea works. The learner has to pick the right one. The target is the right proposition. Take the lure from the candidates, from `graph_find`, or from a common confusion. Name it in the solution, not in `targets`.
3. **composition** - the problem needs several ideas in a row. The learner runs the whole chain. The target is the chain id.

Within a sitting, track each target's mode yourself. A clean solve moves a target to the next mode. Anything else keeps it in the same mode.

Across sittings, the tools don't say which mode a target last had. Use this instead:

- A proposition whose `lastOutcome` is `solved`: discrimination.
- Any other proposition: recall.
- A chain: composition, once none of its premises is in `due`.

## Choosing the next target

The opening of a sitting is the one exception: it takes easy targets (see "A sitting"). After it:

1. **Due targets first**, from `due`. Among them, the weakest first (`surrendered` and `movedOn`, then `solvedWithHints`, then `solved`), then the most used, then the least recent (`due` is already longest overdue first).
2. **Then candidates**, most used first. A target that is not due was practiced recently or never; both are fine to use.

**Most used** means it appears in the most chains in `candidates.chains`, as a premise or as the conclusion. An idea many chains depend on matters most.

**Interleave.** Switch target on every problem, and mix modes and areas when you can. Never block: no runs of problems on one target. A miss does not mean "drill it now". It goes on the list of misses for the close.

## Difficulty

Aim for about 85% success per moment, not per problem. A composition problem with three moments fails more often as a whole than a recall problem, and that is expected.

There is no difficulty field. Difficulty lives in the statement and in `cue_class`. The knobs:

- **Cue distance**, recorded as `cue_class`:
  - `near` - the problem looks like where the idea was taught.
  - `far` - a new setting, but the surface still hints at the idea's area.
  - `bare` - nothing on the surface points at the idea's area.
- **How close the lure is** (discrimination).
- **How many ideas run in a row**, and how many of the steps the learner has to see without help (composition).
- **Details that don't matter**, which the learner has to set aside.

After each problem on a target:

- A clean solve (`solved`): one notch harder next time.
- A solve after a hint or a wrong answer (`solvedWithHints`): the same.
- No solve (`surrendered` or `movedOn`): one notch easier.

A target new to this sitting starts at `far` if its `lastOutcome` is `solved`, and at `near` otherwise.

## Building a problem

Commit first. Before the learner sees anything:

1. **Write the statement.** A concrete task with one clear question. It never names the target idea, its usual name, or the key words of its `statement`. Compare your statement with the target's statement text and take out any word that gives it away.
2. **Solve it yourself**, step by step. If you can't reach one clean answer, fix the problem or drop it.
3. **Look for a shortcut** that skips the target: guessing from the numbers, a simpler idea that also works, a hint in the wording, the shape of the expected answer. If you find one, change the problem to close it, then solve it again.
4. **Write the solution** for the learner: the answer, the worked steps, and the idea it used, stated in full. For discrimination, also say why the lure fails.
5. **Call `commit_problem`.** Show the statement only after it returns, word for word as committed.

## Hints

Give a hint when the learner asks for one. Each request climbs one rung. Give the lowest rung that would unblock them, never more than one above the last rung given.

- **R0** - point at a detail in the problem worth a second look.
- **R1** - name the kind of pattern ("something here stays the same").
- **R2** - name the family of ideas the answer comes from.
- **R3** - name the idea.
- **R4** - outline the move: what to do with the idea here, without doing it.
- **R5** - work the step with them, then let them finish.

Below R3, never name the idea. Remember the highest rung given: it is `rung`.

## Wrong answers

1. Say it is wrong, plainly.
2. Point at the first place their work breaks. Don't give the fix.
3. Nudge: one short question or pointer, and let them try again. If no hint was given yet, the nudge counts as R0.

If they gave only an answer, ask how they got it before you point at a break.

Then classify the miss:

- **cue** - they didn't think of the idea at all.
- **discrimination** - they used a similar wrong idea, often the lure.
- **execution** - the right idea, carried out wrong.
- **careless** - a slip they fix at once when it is pointed at.
- **structural** - the idea itself is wrong in their head.

A problem records one class. With several misses, keep the most serious: structural, then discrimination, then cue, then execution, then careless.

A structural miss needs repair. After the reveal, fix the idea in a few sentences, built from what they already hold, and retest it at the close. If it needs more than that, suggest a `/study` goal for it.

## Ending a problem

End a problem only when the learner solved it or ended it themselves: they gave up, asked for the answer, or asked to skip. Never end it because it is taking long. Then call `conclude_problem`, show the solution it returns, and end the turn. The next problem waits for the learner.

## Recording a problem

`conclude_problem` takes:

- **`outcome`**
  - `solved` - right on the first answer, with no hint.
  - `solvedWithHints` - right in the end, after a hint or a wrong answer.
  - `surrendered` - they gave up or asked for the answer.
  - `movedOn` - they ended it another way: a skip, a different problem, a stop, or a flaw in the problem.
- **`verdict`** - the grade of their last answer: `right`, `partly`, `wrong`, or `dontKnow` when they gave none.
- **`rung`** - the highest rung given, `"R0"` to `"R5"`, or null for no hint.
- **`miss_class`** - the class above, or null when there was no miss. Giving up because the idea never came is `cue`.
- **`retest`** - true when the target should come back in a new form: any miss, a surrender, a move-on that left the idea untested, a solve that needed R3 or higher, or a right answer that looked lucky. Otherwise false. A retest at the close gets its own value by the same rule.

Record what happened, not what you hoped. An outcome marked better than it was pushes the next review weeks out.

## The due list

The server works out when each target is due again, from its latest conclude:

- `movedOn`, `surrendered`, a rung of R3 or higher, or `retest` set: in 1 day.
- `solvedWithHints` with R0 to R2: in 3 days.
- `solved` with no hint: double the previous gap, at least 3 days and at most 60.

`due` holds the targets due now, longest overdue first. A target never practiced is not on it. Nothing reminds the learner outside a session: the list is read when `/practice` starts.

## A sitting

- **Opening:** one to three easy recall problems, `near` cue, on targets the learner probably holds. They warm up and show the level.
- **Middle:** interleaved. A new target every problem, modes and areas mixed, difficulty moving per target as above.
- **Close:** retest every miss of this sitting in a new form: the same target, a new setting and a new surface, the same mode or an easier one. Each retest is a normal commit and conclude.
- **Length** is the learner's choice. When they say they want to stop, run the close first (they may decline), then `end_session`.
