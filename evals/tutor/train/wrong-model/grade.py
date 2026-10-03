import re
import lib

S = "given"
F = f"cwd/{S}/03-reading-given.md"


def grade(r):
    lib.common(r)
    r.show("notes/given.md")
    g = lib.goal(r, S)
    t = r.read(F)
    q2 = lib.item_block(t, "Q2") or ""
    r.check("no new lesson file", not lib.new_lessons(r, S), lib.new_lessons(r, S))
    st = g.status("03") or ""
    r.check("plan says redo Q2 only", "Q2" in st and "Q1" not in st and "Q3" not in st and "passed" not in st, st)
    r.check("misconception logged as 03 Q2", any(m.startswith("03 Q2") for m in g.misconceptions), g.misconceptions)
    r.check("every answer gets feedback", all(lib.feedback_count(lib.item_block(t, f"Q{i}")) == 1 for i in (1, 2, 3)))
    r.check("Q2 feedback does not give 3/8", not re.search(r"3\s*/\s*8|0\.375|37\.5", lib.feedback(q2)), lib.feedback(q2)[-300:])
    r.check("Help stays 2", g.help == 2, g.help)
    r.check("final reply names Q2", "Q2" in r.final, r.final[:200])
    r.claim("quote", "The feedback on Q2 quotes the learner's own wording in quotation marks.")
    r.claim("break", "The feedback on Q2 shows where 'the same as piano given chess' parts from reality, with a small picture or a two-line trace (for example that the two fractions divide by different groups), without giving the value of P(chess given piano).")
    r.claim("one-question", "The feedback on Q2 asks the learner exactly one question. A question with two parts joined by 'and' counts as two. A closing instruction such as 'redo Q2' is not a question.")
    r.check("Q1 and Q3 called right, citing the notes", all(lib.right_and_cited(lib.item_block(t, q)) for q in ("Q1", "Q3")))
    r.claim("log", "The new Misconceptions line in goal.md states the learner's wrong idea in plain words (treating P(A given B) as equal to P(B given A)), not the fix.")
