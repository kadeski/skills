import re
import lib

S = "loop-counting"
F01 = f"cwd/{S}/01-where-youre-at.html"


def grade(r):
    lib.common(r)
    r.show("notes/big-o.md")
    g = lib.goal(r, S)
    t01 = r.read(F01)
    r.check("Help rises to 3", g.help == 3, g.help)
    r.check("01 marked passed", "passed" in (g.status("01") or ""), g.status("01"))
    r.check("01 not marked first try", "first try" not in (g.status("01") or ""), g.status("01"))
    r.check("Q1 misconception logged as 01 Q1", any(m.startswith("01 Q1") for m in g.misconceptions), g.misconceptions)
    r.check("Q1 to Q3 get feedback", all(lib.feedback_count(lib.item_block(t01, f"Q{i}")) >= 1 for i in (1, 2, 3)))
    new = lib.new_lessons(r, S)
    r.check("lesson 02 written", len(new) == 1 and re.search(r"/02-", new[0]), new)
    r.check("lesson 02 linked in the plan", "02" in g.plan and "](02-" in g.plan["02"][0], g.plan.get("02"))
    if not new:
        return
    t02 = r.read(new[0])
    r.check("02 reveals the guess", lib.section(t02, "Your guess") is not None)
    r.check("02 has 2 or 3 questions", len(lib.items(t02)) in (2, 3), lib.items(t02))
    q1 = lib.item_block(t01, "Q1") or ""
    fb = lib.feedback(q1)
    r.check("Q1 feedback asks no question (lesson 01 rule)", fb and "?" not in fb, fb.strip()[:200])
    r.claim("q1-shows-break", "In lesson 01, the feedback on Q1 quotes the learner's answer in quotation marks and shows why range(2, 10) does not reach 10, for example by listing the values or citing the notes.")
    r.claim("q2-gap", "In lesson 01, the feedback on Q2 teaches what n squared means using an example other than n = 1000, and does not state the value of 1000 squared.")
    r.claim("retest", "The first question of the new lesson 02 tests again whether a range stops before its end value, on new numbers.")
    r.claim("help3", "Lesson 02 includes a worked example traced step by step before its questions, and says near the top that the help level went up.")
    r.claim("reveal", "Lesson 02's Your guess section says the learner picked c) 3n and that 3n is right.")
