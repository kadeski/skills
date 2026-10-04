import re
import lib

S = "adding-fractions"
F = f"cwd/{S}/03-different-bottoms.html"


def grade(r):
    lib.common(r)
    r.show("notes/fractions.md")
    g = lib.goal(r, S)
    t = r.read(F) or ""
    q2 = lib.item_block(t, "Q2") or ""
    st = g.status("03") or ""
    r.check("03 marked passed, first try", "passed, first try" in st and "redo" not in st and "Q2" not in st, st)
    r.check("You can now line in 03", any(p.startswith("You can now ") for p in lib.passes(t)))
    r.check("every answer gets feedback", all(lib.feedback_count(lib.item_block(t, f"Q{i}")) == 1 for i in (1, 2, 3)))
    r.check("Q2 answer left as 14/24", any(re.search(r"= 14/24 \(sure\)$", a) for a in lib.answers(q2)), lib.answers(q2))
    r.check("Q2 not logged as a misconception", not any(m.startswith("03 Q2") for m in g.misconceptions), g.misconceptions)
    r.check("Help stays 2", g.help == 2, g.help)
    r.check("new rule r03 due in 2 days", g.rule_next("r03") == r.d(2) and g.rule_gap("r03") == 2, g.rules.get("r03"))
    r.check("r02 not moved", g.rule_next("r02") == r.d(1) and g.rule_gap("r02") == 2, g.rules.get("r02"))
    new = lib.new_lessons(r, S)
    r.check("lesson 04 written and linked", len(new) == 1 and "/04-" in new[0] and "](04-" in (g.plan.get("04") or [""])[0], new)
    t04 = r.read(new[0]) if new else ""
    if new:
        r.check("04 reveals the guess", lib.section(t04, "Your guess") is not None)
    r.claim("odd-form-right", "The feedback on Q2 says the learner's answer 14/24 is right. It does not call it wrong, partly right or incomplete, and does not ask the learner to simplify or change it. Noting that 14/24 equals 7/12 is allowed.")
    r.check("Q1 and Q3 called right, citing the notes", all(lib.right_and_cited(lib.item_block(t, q)) for q in ("Q1", "Q3")))
    lib.control_claims(r, t04, "lesson 04")
