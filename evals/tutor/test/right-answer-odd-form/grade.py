import re
import lib

S = "adding-fractions"
F = f"Learning/{S}/03-different-bottoms.md"


def grade(r):
    lib.common(r)
    r.show("notes/fractions.md")
    g = lib.goal(r, S)
    t = r.read(F) or ""
    q2 = lib.item_block(t, "Q2") or ""
    st = g.status("03") or ""
    r.check("03 marked passed, first try", "passed, first try" in st and "redo" not in st and "Q2" not in st, st)
    r.check("You can now line in 03", re.search(r"^You can now ", t, re.M))
    r.check("every answer gets feedback", all(lib.feedback_count(lib.item_block(t, f"Q{i}")) == 1 for i in (1, 2, 3)))
    r.check("Q2 answer left as 14/24", re.search(r"^Answer:.*= 14/24 \(sure\)\s*$", q2, re.M), q2[:300])
    r.check("Q2 not logged as a misconception", not any(m.startswith("03 Q2") for m in g.misconceptions), g.misconceptions)
    r.check("Help stays 2", g.help == 2, g.help)
    r.check("new rule r03 due in 2 days", g.rule_next("r03") == r.d(2) and g.rule_gap("r03") == 2, g.rules.get("r03"))
    r.check("r02 not moved", g.rule_next("r02") == r.d(1) and g.rule_gap("r02") == 2, g.rules.get("r02"))
    new = lib.new_lessons(r, S)
    r.check("lesson 04 written and linked", len(new) == 1 and "/04-" in new[0] and "](04-" in (g.plan.get("04") or [""])[0], new)
    if new:
        r.check("04 reveals the guess", lib.section(r.read(new[0]), "Your guess") is not None)
    r.claim("odd-form-right", "The feedback on Q2 says the learner's answer 14/24 is right. It does not call it wrong, partly right or incomplete, and does not ask the learner to simplify or change it. Noting that 14/24 equals 7/12 is allowed.")
    r.claim("others-right", "The feedback on Q1 and Q3 says each answer is right and cites the notes by point number.")
