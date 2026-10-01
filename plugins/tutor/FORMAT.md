# File format

Plain CommonMark plus tables and `$math$`, so every markdown app shows the same thing: headings, bold, lists, blockquotes, code (inline and fenced), tables without math, relative links, SVG images.

- No HTML, callouts, mermaid, wikilinks, frontmatter or checkboxes.
- File and image names have no spaces. A web link goes in angle brackets: `<https://...>`.
- Math: `$x$` inline with no spaces inside the dollars, `$$` on their own lines. Never a `$` for money.
- One item per line: each option, each field. Apps that drop line breaks run the rest together.
- A code question gets an empty fenced block after `Answer:`.

## goal.md

```markdown
# Stars and Bars

- Goal: pick the right counting formula on sight and compute it in under a minute.
- Source: course study guide 4.9, 4.10
- Exam: 2026-10-20
- Help: 2

## Plan

- [01 Where you're at](01-where-youre-at.md) - passed 2026-09-08
- [02 Bars make bins](02-bars-make-bins.md) - passed 2026-09-09
- [03 At least one each](03-at-least-one-each.md) - redo Q2
- 04 Pick the formula

## Rules

- r02 n identical items into k bins: C(n+k-1, k-1) - next 2026-09-11, gap 2

## Misconceptions

- 2026-09-09 02 Q3: treats identical items as distinct (k^n). Watch on every counting item.
```

A linked lesson with no status is waiting for answers. A pass where no answer needed a redo adds `, first try`. A learned rule gets `learned` in place of its next date. Leave out `## Rules` and `## Misconceptions` until they have an entry.

## A lesson file

The learner types after each `Answer:`. Due review questions go first, under `## Review`, numbered R1, R2 like any question. Lesson 01 has only the title, the Part-of line, `## Questions` (a data table above them if needed) and `## Guess for next time`. A review file has only the title, the Part-of line and `## Review`.

```markdown
# 02 Bars make bins

Part of [Stars and Bars](goal.md). Add `sure` or `guess` after any answer, and say `done` when finished.

## Your guess

Last time: how many ways to hand 5 identical cookies to 3 kids? You said **b) 15**. It is **c) 21**.

![Five stars split by two bars into piles of 2, 2 and 1](img/02-bars-make-bins.svg)

- a) 10 picks 3 of the 5 cookies, but with identical cookies "which ones" means nothing.
- b) 15 multiplies 5 by 3, as if each kid made one choice.
- c) 21: each handout is a row of 5 stars and 2 bars, and there are $\binom{7}{2} = 21$ ways to place the bars.
- d) 243 is $3^5$, each cookie picking a kid. That treats the cookies as different.

## The idea

Line the 5 cookies up as stars. Two bars cut the row into 3 piles, one per kid: `**|**|*` is 2, 2, 1, and `|*****|` is 0, 5, 0. Every handout is one row, and every row is one handout. So count the rows: 7 spots, choose 2 for the bars.

$$
\binom{n+k-1}{k-1} \quad \text{for } n \text{ identical items into } k \text{ bins}
$$

Source: course study guide 4.9.

## Questions

**Q1.** 4 identical pens go into 2 cups. Why does the row need exactly 1 bar?

Answer:

**Q2.** 7 identical stickers go into 4 jars. How many ways?

Answer:

**Q3.** Sam says 3 identical balls into 2 boxes is $2^3 = 8$ ways, "because each ball picks a box." What is wrong?

Answer:

## Guess for next time

Not graded: the next lesson shows the answer.

Now every kid gets at least one cookie. How many ways to hand 5 identical cookies to 3 kids?

- a) 6
- b) 10
- c) 15
- d) 21

Answer:
```

## After grading

Feedback goes in a quote under each answer. A picture in feedback goes right after the quote, named after its lesson (`img/02-swap.svg`).

```markdown
**Q3.** Sam says 3 identical balls into 2 boxes is $2^3 = 8$ ways, "because each ball picks a box." What is wrong?

Answer: each ball can go in 2 boxes so it's 2x2x2 (sure)

> **Feedback:** "each ball can go in 2 boxes" counts these two as different:
>
> - ball 1 in A, balls 2 and 3 in B: `*|**`
> - ball 2 in A, balls 1 and 3 in B: `*|**`
>
> How many different rows are there? (study guide 4.9)
```

On a pass, the last line of the lesson, after the guess, is: `You can now count handouts of identical items. The rule is r02 in goal.md.`

## A picture

A plain SVG file: width, height and viewBox set, its own white background and dark strokes so it reads in dark themes, no scripts or external fonts.
