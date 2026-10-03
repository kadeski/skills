import lib

F = "cwd/percent-change/01-where-youre-at.html"


def grade(r):
    lib.common(r)
    r.show("notes/percent.md")
    t = r.read(F)
    g = lib.goal(r, "percent-change")
    r.check("no new lesson file", not lib.new_lessons(r, "percent-change"), lib.new_lessons(r, "percent-change"))
    r.check("01 now has 5 questions", lib.items(t) == ["1", "2", "3", "4", "5"], lib.items(t))
    r.check("Q1 to Q3 get feedback", all(lib.feedback_count(lib.item_block(t, f"Q{i}")) == 1 for i in (1, 2, 3)))
    r.check("new questions are unanswered", all(lib.item_block(t, f"Q{i}") is not None and not lib.history(lib.item_block(t, f"Q{i}")) for i in (4, 5)))
    r.check("01 not marked passed yet", "passed" not in (g.status("01") or ""), g.status("01"))
    r.check("Help stays 2", g.help == 2, g.help)
    r.claim("harder", "The two new questions in lesson 01 (Q4 and Q5) are clearly harder than Q1 to Q3, for example multi-step or with less friendly numbers.")
    r.claim("still-prereq", "Q4 and Q5 still check skills that finding a percent of a number builds on (decimals, fractions, multiplying by a decimal). Neither asks the learner to find a percent of a number or a percent change, which later lessons teach.")
    r.claim("reply", "The tutor's final reply says lesson 01 got harder questions (or is not passed yet) and gives the path of the file to open.")
