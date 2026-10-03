import re
import lib

S = "angle-facts"
F07 = f"cwd/{S}/07-outside-angles.md"
R1_ANSWER = "75, angles at a point make 180 like on a straight line"

# An option line: "- a) 40", "a) 40", "- **b)** 40"
OPTION = re.compile(r"^\s*(?:[-*+]\s+)?\**\(?([a-eA-E])[).]\**\s+(.*)$", re.M)
REASONING = re.compile(r"\b(?:because|since|so|means|as it|which|that is)\b|:", re.I)


def options(block):
    return OPTION.findall(block or "")


def quotes_learner(fb, answer):
    """A quoted stretch of 8+ characters taken from the learner's answer."""
    norm = lambda s: re.sub(r"\s+", " ", s).strip().lower()
    return any(len(q) >= 8 and norm(q) in norm(answer) for q in re.findall(r'["“]([^"”\n]+)["”]', fb))


def grade(r):
    lib.common(r)
    r.show("notes/angles.md")
    g = lib.goal(r, S)
    before = lib.goal_before(r, S)
    t07 = r.read(F07) or ""
    st = g.status("07") or ""
    fb1 = lib.feedback(lib.item_block(t07, "R1"))

    # grading lesson 07
    r.check("07 marked passed, first try (a wrong review answer never blocks)", "passed, first try" in st, st)
    r.check("You can now line in 07", re.search(r"^You can now ", t07, re.M))
    r.check("Q1 to Q3 and R1 each get one feedback",
            all(lib.feedback_count(lib.item_block(t07, x)) == 1 for x in ("Q1", "Q2", "Q3", "R1")))
    uncited = [x for x in ("Q1", "Q2", "Q3", "R1") if not re.search(r"notes\D{0,12}\d", lib.feedback(lib.item_block(t07, x)))]
    r.check("every feedback in 07 cites the notes by point", not uncited, uncited)
    r.check("R1 feedback quotes the learner's answer", quotes_learner(fb1, R1_ANSWER), fb1[:300])
    r.check("R1 feedback does not give x = 255", fb1 and "255" not in fb1, fb1[:300])
    r.check("R1 wrong model logged", len(g.misconceptions) == len(before.misconceptions) + 1, g.misconceptions)
    r.check("r03 answered wrong: back to 1 day", g.rule_next("r03") == r.d(1) and g.rule_gap("r03") == 1, g.rules.get("r03"))
    r.check("r02 still learned", g.rule_learned("r02") and not g.rule_next("r02"), g.rules.get("r02"))
    r.check("r04, r05 and r06 not moved before they are answered",
            all(g.rules.get(x) == before.rules.get(x) for x in ("r04", "r05", "r06")),
            [g.rules.get(x) for x in ("r04", "r05", "r06")])
    r.check("new rule r07 due in 2 days", g.rule_next("r07") == r.d(2) and g.rule_gap("r07") == 2, g.rules.get("r07"))
    r.check("Help drops to 1 (06 and 07 first try in a row)", g.help == 1, g.help)
    r.check("no lesson 08 added to the plan", "08" not in g.plan, list(g.plan))
    r.claim("r1-break", "The feedback on R1 in lesson 07 shows where 'angles at a point make 180' parts from reality, with a small picture or a two-line trace (for example a point split by two straight lines), rather than only stating the rule.")
    r.claim("r1-one-question", "The feedback on R1 in lesson 07 asks exactly one question, not two questions or one question with two parts joined by 'and' or 'so'.")

    # the review file
    rf = f"cwd/{S}/review-{r.d(0)}.md"
    new = lib.new_lessons(r, S)
    r.check("exactly one new file, review-<today>.md, and no new lesson", new == [rf], new)
    r.check("final reply gives the review file's path", f"review-{r.d(0)}" in (r.final or ""), (r.final or "")[:200])
    if rf not in new:
        return
    t = r.read(rf) or ""
    rev = lib.section(t, "Review")
    rs = lib.items(rev or "", "R")
    r.check("review file has 3 R items under Review (r04, r05, r06)", rs == ["1", "2", "3"], rs)
    r.check("review file has no Q items and no guess", not lib.items(t) and "Guess for next time" not in t, lib.items(t))
    labels = [f"R{i}" for i in rs]
    opts = {x: options(lib.item_block(t, x)) for x in labels}
    mc = [x for x in labels if opts[x]]
    bad = {x: len(o) for x, o in opts.items() if o and [k.lower() for k, _ in o] != list("abcd")}
    r.check("every mc item has exactly 4 options, a to d", not bad, bad)
    reasoning = [f"{x}: {o}" for x in mc for _, o in opts[x] if REASONING.search(o)]
    r.check("no option holds reasoning", not reasoning, reasoning[:4])
    r.check("no item tests r07, which is not due (outside angles)", not re.search(r"outside|exterior|extend", t, re.I),
            re.findall(r"[^\n]*(?:outside|exterior|extend)[^\n]*", t, re.I)[:2])

    r.claim("review-r04", "Some R item in the review file tests r04 (where two lines cross, opposite angles are equal) on a case other than lesson 04's 40 and 140 picture and its 65 question.")
    r.claim("review-r05", "Some R item in the review file tests r05 (the angles in a triangle add up to 180) on a case other than lesson 05's 50 and 70, 25 and 110, right angle and 38, or 100 and 90.")
    r.claim("review-r06", "Some R item in the review file tests r06 (the base angles of an isosceles triangle are equal) on a case other than lesson 06's top angle 40, base angles 52, or top angle 100.")
    r.claim("kinds", "Every R item in the review file is multiple choice or asks for a single number; none asks the learner to explain in words.")
    for x in mc:
        r.claim(f"shape-{x}", f"Item {x} in the review file has 4 options in the same shape (for example all bare angles in degrees), none longer or more detailed than the others, so they cannot be told apart without the material.")
    if len(mc) >= 2:
        r.claim("letters", "Working out each multiple-choice item in the review file, the right answer does not sit at the same letter in all of them.")
    r.claim("accurate", "Every R item in the review file has one right answer, that answer is correct (check the arithmetic), and for multiple choice it is among the options.")
