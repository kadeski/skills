import re
import lib

S = "percent-change"
F = f"cwd/{S}/03-percent-change.md"


def grade(r):
    lib.common(r)
    r.show("notes/percent.md")
    g = lib.goal(r, S)
    t = r.read(F)
    q1 = lib.item_block(t, "Q1") or ""
    q3 = lib.item_block(t, "Q3") or ""
    st = g.status("03") or ""
    r.check("no new lesson file", not lib.new_lessons(r, S), lib.new_lessons(r, S))
    r.check("plan says redo Q1 and Q3", "Q1" in st and "Q3" in st and "Q2" not in st and "passed" not in st, st)
    r.check("slip not logged as a misconception", not any(m.startswith("03 Q1") for m in g.misconceptions), g.misconceptions)
    r.check("Help stays 2", g.help == 2, g.help)
    r.check("Q1 feedback does not give 20%", not re.search(r"\b20 ?%|= ?0\.20?\b", lib.feedback(q1)), lib.feedback(q1)[:300])
    r.check("Q1, Q2 and Q3 get feedback", all(lib.feedback_count(lib.item_block(t, f"Q{i}")) == 1 for i in (1, 2, 3)))
    r.check("final reply names Q1 and Q3", "Q1" in r.final and "Q3" in r.final, r.final[:200])
    r.claim("slip", "The learner's Q1 answer has an arithmetic slip: 50 / 250 is 0.2, not 0.25, so the right answer is 20%. The feedback on Q1 catches this and treats it as a slip: it points at the step 50 / 250 and asks the learner to check it, without saying what 50 / 250 is.")
    r.claim("gap", "The feedback on Q3 teaches why the change is measured against the old value using a new example (not 250 to 300 or 800 to 600), and leaves the learner to put the reason in their own words.")
    r.claim("q2", "The feedback on Q2 says the answer is right and cites the notes.")
