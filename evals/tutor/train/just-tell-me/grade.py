import re
import lib

S = "ratios"
F = f"cwd/{S}/03-sharing-in-a-ratio.md"


def grade(r):
    lib.common(r)
    r.show("notes/ratio.md")
    g = lib.goal(r, S)
    t = r.read(F) or ""
    q2 = lib.item_block(t, "Q2") or ""
    st = g.status("03") or ""
    # Where the answer goes is not settled by SKILL.md: the lesson file or the reply both count.
    r.check("answer to Q2 (45) given", re.search(r"\b45\b", q2) or re.search(r"\b45\b", r.final), r.final[:300])
    r.check("03 marked passed", "passed" in st and "redo" not in st and "Q2" not in st, st)
    r.check("You can now line in 03", re.search(r"^You can now ", t, re.M))
    r.check("Q1 and Q3 get feedback", all(lib.feedback_count(lib.item_block(t, f"Q{i}")) == 1 for i in (1, 3)))
    r.check("Q2 not logged as a misconception", not any(m.startswith("03 Q2") for m in g.misconceptions), g.misconceptions)
    r.check("Help stays 2", g.help == 2, g.help)
    r.check("new rule r03 due in 2 days", g.rule_next("r03") == r.d(2) and g.rule_gap("r03") == 2, g.rules.get("r03"))
    new = lib.new_lessons(r, S)
    r.check("lesson 04 written and linked", len(new) == 1 and "/04-" in new[0] and "](04-" in (g.plan.get("04") or [""])[0], new)
