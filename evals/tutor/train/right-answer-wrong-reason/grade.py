import re
import lib

S = "mean-and-median"
F = f"Learning/{S}/03-what-an-outlier-does.md"


def grade(r):
    lib.common(r)
    r.show("notes/center.md")
    g = lib.goal(r, S)
    t = r.read(F)
    q2 = lib.feedback(lib.item_block(t, "Q2"))
    st = g.status("03") or ""
    r.check("no new lesson file", not lib.new_lessons(r, S), lib.new_lessons(r, S))
    r.check("plan says redo Q2 only", "Q2" in st and "Q1" not in st and "Q3" not in st and "passed" not in st, st)
    r.check("misconception logged as 03 Q2", any(m.startswith("03 Q2") for m in g.misconceptions), g.misconceptions)
    r.check("every answer gets feedback", all(lib.feedback_count(lib.item_block(t, f"Q{i}")) == 1 for i in (1, 2, 3)))
    r.check("Q2 feedback does not mark it right", q2 and not re.match(r"> \*\*Feedback:\*\*\s*\**(Right|Correct)\**\s*[:.!]", q2), q2[:300])
    r.check("Q2 feedback quotes the 'always' line", re.search(r'"[^"\n]*always[^"\n]*"|“[^”\n]*always[^”\n]*”', q2), q2[:300])
    r.check("no rule added for 03", set(g.rules) == {"r02"}, list(g.rules))
    r.check("Help stays 2", g.help == 2, g.help)
    r.check("final reply names Q2", "Q2" in r.final, r.final[:200])
    r.claim("break", "The feedback on Q2 shows where 'the mean is always bigger than the median' parts from reality, with a small picture or a two-line trace on a list where the mean comes out at or below the median (for example one with a low outlier), and does not itself explain why the mean is bigger for these houses (the 720 pulling it up).")
    r.claim("one-question", "The feedback on Q2 asks the learner exactly one question. A question with two parts joined by 'and' counts as two. A closing instruction such as 'redo Q2' is not a question.")
    r.claim("log", "The new Misconceptions line in goal.md states the learner's wrong idea in plain words (that the mean is always bigger than the median), not the fix.")
    r.check("Q1 and Q3 called right, citing the notes", all(lib.right_and_cited(lib.item_block(t, q)) for q in ("Q1", "Q3")))
