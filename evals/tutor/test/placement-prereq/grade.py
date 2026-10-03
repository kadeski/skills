import re
import lib

S = "right-triangles"
F01 = f"cwd/{S}/01-where-youre-at.md"


def find(g, pattern):
    """Plan number of the first entry whose line matches pattern."""
    return next((n for n, (line, _) in g.plan.items() if re.search(pattern, line, re.I)), None)


def grade(r):
    lib.common(r)
    r.show("notes/right-triangles.md")
    g = lib.goal(r, S)
    t01 = r.read(F01)
    st = g.status("01") or ""
    r.check("Help rises to 3", g.help == 3, g.help)
    r.check("01 marked passed, no redo", "passed" in st and "redo" not in st, st)
    r.check("01 not marked first try (Q2 is tagged guess)", "first try" not in st, st)
    r.check("Q1 to Q3 get feedback", all(lib.feedback_count(lib.item_block(t01, f"Q{i}")) >= 1 for i in (1, 2, 3)))
    r.check("no misconception logged (guess and blank are gaps)", not g.misconceptions, g.misconceptions)
    r.check("no rule added (01 teaches none)", not g.rules, list(g.rules))

    rule = find(g, r"right.triangle rule|pythag")
    leg = find(g, r"missing leg")
    r.check("plan gains one lesson (5 in all)", len(g.plan) == 5, list(g.plan))
    r.check("new plan entry 02 sits before the right-triangle rule and missing-leg lessons",
            "02" in g.plan and rule and leg and "02" < rule < leg
            and not re.search(r"right.triangle rule|pythag|missing leg|drill", g.plan["02"][0], re.I),
            [line for line, _ in g.plan.values()])
    new = lib.new_lessons(r, S)
    r.check("one new lesson file, 02, linked from the plan",
            len(new) == 1 and re.search(r"/02-[^/]+\.md$", new[0])
            and f"]({new[0].rsplit('/', 1)[1]})" in (g.plan.get("02") or [""])[0], new)
    if not new:
        return
    t02 = r.read(new[0])
    r.check("new lesson has 2 or 3 questions", len(lib.items(t02)) in (2, 3), lib.items(t02))
    r.claim("prereq-lesson", "The new lesson 02 teaches squaring a number and taking a square root, and does not teach the right-triangle rule a^2 + b^2 = c^2.")
    r.claim("gap-teaching", "In lesson 01, the feedback on Q2 teaches what squaring means using a number other than 7, and the feedback on Q3 teaches what a square root is using a number other than 81.")
    r.claim("help3", "The new lesson 02 says near the top that the help level went up, and includes a worked example traced step by step before its questions.")
