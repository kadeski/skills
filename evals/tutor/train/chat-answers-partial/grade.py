import lib

S = "order-of-operations"
F = f"cwd/{S}/03-left-to-right.html"
Q2 = "Jo multiplied first, but x and / share a rank so you go from the left: 24/4 = 6, then 6 x 2 = 12 (sure)"


def grade(r):
    lib.common(r)
    t = r.read(F) or ""
    r.check("only the lesson file changed", r.changed_files() == [F], r.changed_files())
    r.check("no files created", not r.new_files(), r.new_files())
    r.check("Q2 answer copied word for word with its tag", lib.answers(lib.item_block(t, "Q2")) == [Q2],
            lib.answers(lib.item_block(t, "Q2")))
    guess = lib.section(t, "Guess for next time (not graded)")
    r.check("guess answer copied as written", lib.answers(guess) == ["b"], lib.answers(guess))
    r.check("Q1 and Q3 still blank",
            not any(lib.answers(lib.item_block(t, q)) for q in ("Q1", "Q3")),
            [lib.answers(lib.item_block(t, q)) for q in ("Q1", "Q3")])
    r.check("nothing graded", lib.feedback_count(t) == 0, lib.feedback_count(t))
    lines = [x for x in r.final.strip().splitlines() if x.strip()]
    r.check("reply is one line", len(lines) == 1, r.final[:300])

    r.claim("ask", "The tutor's reply says Q2 and the guess were recorded, names Q1 and Q3 as blank, and asks whether the learner is done or wants to answer them first.")
    r.claim("no-grade", "The tutor's reply does not say whether the Q2 answer is right and does not give the answer to Q1 or Q3.")
