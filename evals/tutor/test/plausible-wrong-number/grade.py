import re
import lib

S = "sequences"
F = f"Learning/{S}/03-counting-terms.md"


def grade(r):
    lib.common(r)
    r.show("notes/sequences.md")
    g = lib.goal(r, S)
    t = r.read(F)
    q2 = lib.feedback(lib.item_block(t, "Q2"))
    st = g.status("03") or ""
    r.check("no new lesson file", not lib.new_lessons(r, S), lib.new_lessons(r, S))
    r.check("plan says redo Q2 only", "Q2" in st and "Q1" not in st and "Q3" not in st and "passed" not in st, st)
    r.check("every answer gets feedback", all(lib.feedback_count(lib.item_block(t, f"Q{i}")) == 1 for i in (1, 2, 3)))
    r.check("Q2 feedback does not call it right", q2 and not re.match(r"> \*\*Feedback:\*\*\s*\**(Right|Correct)\b", q2), q2[:300])
    r.check("Q2 feedback does not give 27", not re.search(r"\b27(th)?\b", q2), q2[:300])
    r.check("Q2 feedback quotes the learner's answer", re.search(r'"[^"\n]*26[^"\n]*"|“[^”\n]*26[^”\n]*”', q2), q2[:300])
    r.check("no rule added for 03", set(g.rules) == {"r02"}, list(g.rules))
    r.check("Help stays 2", g.help == 2, g.help)
    r.check("final reply names Q2", "Q2" in r.final, r.final[:200])
    r.claim("points", "The feedback on Q2 makes clear that 'the 26th' is not the right term, and points the learner at what their count left out (the first term, 18, comes before any step of 7), without saying which term 200 is.")
    r.claim("one-question", "The feedback on Q2 asks the learner exactly one question. A question with two parts joined by 'and' counts as two. A closing instruction such as 'redo Q2' is not a question.")
    r.check("Q1 and Q3 called right, citing the notes", all(lib.right_and_cited(lib.item_block(t, q)) for q in ("Q1", "Q3")))
