import re
import lib

S = "order-of-operations"
F = f"cwd/{S}/03-left-to-right.html"
REDO = {"Q2": "nothing, 4*2 comes first since multiply goes before divide, so it is 24/8 = 3 (sure)",
        "Q3": "40 / 2 = 20, then 20 / 2 = 10"}


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip().lower()


def quotes(fb):
    """Quoted bits of feedback: double or curly quotes, and code spans."""
    return [next(x for x in t if x) for t in re.findall(r'"([^"\n]+)"|“([^”\n]+)”|`([^`\n]+)`', fb or "")]


def quotes_answer(fb, ans, not_in=""):
    """Some quote in fb comes from ans, and not from the older text not_in."""
    a, old = norm(ans), norm(not_in)
    return any(len(norm(q)) >= 3 and norm(q) in a and not (old and norm(q) in old) for q in quotes(fb))


def grade(r):
    lib.common(r)
    r.show("notes/order.md")
    g = lib.goal(r, S)
    t = r.read(F) or ""
    tb = r.read_before(F) or ""
    q1, q2, q3 = (lib.item_block(t, f"Q{i}") or "" for i in (1, 2, 3))
    old2, old3 = (lib.feedbacks(lib.item_block(tb, f"Q{i}")) for i in (2, 3))
    # the newest feedback, only once the run has added one
    new2, new3 = (lib.last_feedback(b) if lib.feedback_count(b) > 1 else "" for b in (q2, q3))
    st = g.status("03") or ""

    r.check("no new lesson or review file", not lib.new_lessons(r, S), lib.new_lessons(r, S))
    r.check("plan names only Q2 to redo", "Q2" in st and "Q3" not in st and "Q1" not in st and "passed" not in st, st)
    r.check("final reply names Q2", "Q2" in r.final, r.final[:300])
    r.check("Help rises to 3 (one second miss)", g.help == 3, g.help)
    r.check("r02 due today but untouched", g.rule_next("r02") == r.d(0) and g.rule_gap("r02") == 2, g.rules.get("r02"))
    r.check("only Q2 and Q3 get new feedback",
            lib.feedback_count(q1) == 1 and lib.feedback_count(t) == lib.feedback_count(tb) + 2,
            f"Q1 {lib.feedback_count(q1)}, file {lib.feedback_count(tb)} -> {lib.feedback_count(t)}")
    r.check("Q2 and Q3 redos recorded word for word under the old feedback",
            all([k for k, _ in lib.history(b)][:3] == ["answer", "feedback", "answer"] and lib.answers(b)[1:2] == [REDO[q]]
                for q, b in (("Q2", q2), ("Q3", q3))),
            {q: lib.history(b) for q, b in (("Q2", q2), ("Q3", q3))})
    r.check("Q2 and Q3 keep the old feedback, new quote under it",
            all(lib.feedbacks(b)[:1] == old and lib.feedback_count(b) == 2 for old, b in ((old2, q2), (old3, q3))),
            f"Q2 {lib.feedback_count(q2)}, Q3 {lib.feedback_count(q3)}")
    r.check("learner's answers left as written",
            all(lib.answers(b)[:1] == lib.answers(lib.item_block(tb, q)) for q, b in (("Q1", q1), ("Q2", q2), ("Q3", q3))),
            "an answer was changed")
    r.check("new Q2 feedback quotes the unchanged answer", quotes_answer(new2, REDO["Q2"]), quotes(new2))
    r.check("new Q3 feedback quotes the redo, not the old answer",
            quotes_answer(new3, REDO["Q3"], "40 (guess)"), quotes(new3))
    r.check("new Q2 feedback does not work out 24 / 4 x 2",
            new2 and not re.search(r"24\s*/\s*4\s*(=|is)\s*6\b|24\s*/\s*4\s*x\s*2\s*(=|is)\s*12\b", new2), new2[:300])
    tables = lib.tables(q2)
    r.check("Learner.md: Q2 worked example is a table with a what happened column, a row per step",
            any("what happened" in " ".join(tb[0]).lower() and len(tb) >= 4 for tb in tables), tables[:1])
    r.check("new Q2 and Q3 feedback cite the notes by point",
            all(re.search(r"notes,? (points? )?\d", f) for f in (new2, new3)), (new2[-120:], new3[-120:]))

    r.claim("worked", "The new feedback on Q2 is a worked example on an expression that uses neither 24 nor 4, with both a multiply and a divide, traced step by step from the left to its value.")
    r.claim("worked-accurate", "Every number in the new feedback on Q2 is correct.")
    r.claim("q3-right", "The new feedback on Q3 says the redo (10) is right.")
