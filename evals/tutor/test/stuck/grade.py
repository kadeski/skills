import lib

S = "loop-counting"
F = f"cwd/{S}/02-counting-steps-in-one-loop.html"


def grade(r):
    lib.common(r)
    r.show("notes/big-o.md")
    g = lib.goal(r, S)
    t = r.read(F) or ""
    q2 = lib.item_block(t, "Q2") or ""
    r.check("Hint line under Q2", lib.hints(q2), lib.text(q2)[:300])
    r.check("only Q2 gets a hint", len(lib.hints(t)) == 1)
    r.check("Help rises to 3", g.help == 3, g.help)
    r.check("nothing graded", lib.feedback_count(t) == 0)
    r.check("Q2 answer still blank", lib.item_block(t, "Q2") is not None and not lib.answers(q2), lib.answers(q2))
    r.check("no new lesson file", not lib.new_lessons(r, S), lib.new_lessons(r, S))
    r.check("plan status unchanged", g.status("02") == lib.goal_before(r, S).status("02"), g.status("02"))
    r.claim("hint", "The hint under Q2 points the learner toward counting passes and steps per pass without stating the total 2n or the big-O.")
    r.claim("reply", "The tutor's final reply is short and gives the path of the file to open.")
