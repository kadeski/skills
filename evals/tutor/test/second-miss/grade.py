import re
import lib

S = "given"
F = f"Learning/{S}/03-reading-given.md"


def grade(r):
    lib.common(r)
    r.show("notes/given.md")
    g = lib.goal(r, S)
    t = r.read(F)
    q2 = lib.item_block(t, "Q2") or ""
    r.check("no new lesson file", not lib.new_lessons(r, S), lib.new_lessons(r, S))
    r.check("Help rises to 3", g.help == 3, g.help)
    r.check("plan still says redo Q2", "Q2" in (g.status("03") or "") and "passed" not in (g.status("03") or ""), g.status("03"))
    r.check("old Q2 feedback kept and new one added", lib.feedback_count(q2) == 2 and 'You wrote "the same as piano given chess"' in q2, lib.feedback_count(q2))
    r.check("Q2 feedback does not give 3/8", not re.search(r"3\s*/\s*8|0\.375|37\.5", lib.feedback(q2)), lib.feedback(q2)[-300:])
    r.claim("quote-new", "The new feedback on Q2 quotes the learner's redo wording (from 'still 3/12, both questions are about the same 3 people...') in quotation marks.")
    r.claim("worked", "The new feedback on Q2 is a worked example on different numbers (not 40, 12, 8 or 3) that computes both P(A given B) and P(B given A) all the way through and shows they differ.")
    r.claim("not-q2", "The new feedback does not work out Q2 itself, so the learner still has to find P(chess given piano).")
