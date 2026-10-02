import lib

S = "series-circuits"


def grade(r):
    lib.common(r)
    r.show("notes/ohms-law.md")
    g = lib.goal(r, S)
    F = f"Learning/{S}/review-{r.d(0)}.md"
    t = r.read(F) or ""
    r.check("r02 right: doubled gap clamped to the day before the exam", g.rule_next("r02") == r.d(4), g.rules.get("r02"))
    r.check("r03 wrong: back to 1 day", g.rule_next("r03") == r.d(1) and g.rule_gap("r03") == 1, g.rules.get("r03"))
    r.check("r04 right at gap 16: learned", g.rule_learned("r04") and not g.rule_next("r04"), g.rules.get("r04"))
    r.check("r05 not due: unchanged", g.rule_next("r05") == r.d(3) and g.rule_gap("r05") == 4, g.rules.get("r05"))
    r.check("R2 wrong model logged", len(g.misconceptions) == len(lib.goal_before(r, S).misconceptions) + 1, g.misconceptions)
    r.check("every review answer gets feedback", all(lib.feedback_count(lib.item_block(t, f"R{i}")) == 1 for i in (1, 2, 3)))
    r.check("no new lesson or review file", not lib.new_lessons(r, S), lib.new_lessons(r, S))
    r.claim("r2-feedback", "The feedback on R2 quotes the learner's reasoning in quotation marks and shows why a series circuit cannot carry different currents (one path), without simply announcing that c) is right.")
    r.claim("cites", "The feedback on R1 and R3 says the answer is right and cites the notes by point number.")
    r.claim("reply", "The tutor's final reply says what was graded and when the next review is due or what to open next.")
