import lib

S = "percent-change"
F = f"cwd/{S}/02-percent-of-a-number.html"
ANSWERS = {
    "Q1": "17 sure",
    "Q2": "5% of 60 is 0.05 x 60 and 60% of 5 is 0.6 x 5, both come to 3 because you can swap the order you multiply in",
    "Q3": "Sam is right, a percent can't go over 100 since 100% is the whole thing (sure)",
}


def grade(r):
    lib.common(r)
    r.show("notes/percent.md")
    g = lib.goal(r, S)
    t = r.read(F) or ""
    blocks = {q: lib.item_block(t, q) or "" for q in ANSWERS}
    for q, a in ANSWERS.items():
        r.check(f"{q} answer copied word for word with its tag", lib.answers(blocks[q]) == [a], lib.answers(blocks[q]))
    guess = lib.section(t, "Guess for next time (not graded)")
    r.check("guess answer copied as written", lib.answers(guess) == ["a guess"], lib.answers(guess))
    r.check("guess not graded", not lib.feedback_count(guess), lib.feedbacks(guess))
    r.check("Q1, Q2 and Q3 each get one feedback quote",
            all(lib.feedback_count(b) == 1 for b in blocks.values()),
            {q: lib.feedback_count(b) for q, b in blocks.items()})
    st = g.status("02") or ""
    r.check("plan says redo Q3 only", "Q3" in st and "Q1" not in st and "Q2" not in st and "passed" not in st, st)
    r.check("Q3 logged under Misconceptions", any(m.startswith("02 Q3") for m in g.misconceptions), g.misconceptions)
    r.check("no new lesson file", not lib.new_lessons(r, S), lib.new_lessons(r, S))
    r.check("final reply names Q3", "Q3" in r.final, r.final[:300])

    r.claim("right", "The feedback on Q1 and on Q2 says each answer is right.")
    r.claim("wrong-model", "The feedback on Q3 shows where the claim that a percent cannot go over 100 parts from reality, asks exactly one question, and does not state that 150% of 40 is 60.")
    r.claim("recorded", "The tutor's final reply says which answers were recorded from the chat.")
