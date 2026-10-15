import re
import lib

S = "given"
F = f"cwd/{S}/03-reading-given.html"
OLD = "3/12, the same as piano given chess (sure)"
REDO = "still 3/12, both questions are about the same 3 people who do both, so the fraction has to match (sure)"


def grade(r):
    lib.common(r)
    r.show("notes/given.md")
    g = lib.goal(r, S)
    t = r.read(F)
    q2 = lib.item_block(t, "Q2") or ""
    r.check("no new lesson file", not lib.new_lessons(r, S), lib.new_lessons(r, S))
    r.check("Help rises to 3", g.help == 3, g.help)
    r.check("plan still says redo Q2", "Q2" in (g.status("03") or "") and "passed" not in (g.status("03") or ""), g.status("03"))
    r.check("redo recorded word for word under the old feedback",
            [k for k, _ in lib.history(q2)][:3] == ["answer", "feedback", "answer"] and lib.answers(q2)[:2] == [OLD, REDO],
            lib.history(q2))
    r.check("old Q2 feedback kept and new one added",
            lib.feedback_count(q2) == 2 and lib.feedbacks(q2)[0].startswith('You wrote "the same as piano given chess"'),
            lib.feedback_count(q2))
    r.check("Q2 feedback does not give 3/8", not re.search(r"3\s*/\s*8|0\.375|37\.5", lib.feedback(q2)), lib.feedback(q2)[-300:])
    r.claim("quote-new", "The new feedback on Q2 quotes the learner's redo wording (from 'still 3/12, both questions are about the same 3 people...') in quotation marks.")
    r.claim("worked", "The new feedback on Q2 is a worked example on different numbers (not 40, 12, 8 or 3) that computes both P(A given B) and P(B given A) all the way through and shows they differ.")
