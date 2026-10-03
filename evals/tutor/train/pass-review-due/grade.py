import re
import lib

S = "loop-counting"
F03 = f"cwd/{S}/03-nested-loops.md"


def grade(r):
    lib.common(r)
    r.show("notes/big-o.md")
    g = lib.goal(r, S)
    t03 = r.read(F03)
    r.check("03 marked passed, first try", "passed, first try" in (g.status("03") or ""), g.status("03"))
    r.check("You can now line in 03", re.search(r"^You can now ", t03, re.M))
    r.check("every answer gets feedback", all(lib.feedback_count(lib.item_block(t03, f"Q{i}")) == 1 for i in (1, 2, 3)))
    r.check("Help drops to 1", g.help == 1, g.help)
    r.check("new rule r03 due in 2 days", g.rule_next("r03") == r.d(2) and g.rule_gap("r03") == 2, g.rules.get("r03"))
    r.check("r02 not moved before it is answered", g.rule_next("r02") == r.d(-1), g.rules.get("r02"))
    new = lib.new_lessons(r, S)
    r.check("lesson 04 written and linked", len(new) == 1 and "/04-" in new[0] and "](04-" in (g.plan.get("04") or [""])[0], new)
    if not new:
        return
    t04 = r.read(new[0])
    rev = lib.section(t04, "Review")
    r.check("04 has a Review section with one R question", rev is not None and lib.items(rev, "R") == ["1"], lib.items(rev or "", "R"))
    r.check("04 has 5 or 6 drill items", len(lib.items(t04)) in (5, 6), lib.items(t04))
    r.check("04 has no guess for next time (last lesson)", "Guess for next time" not in t04)
    r.claim("review-new-case", "R1 in lesson 04 tests r02 (a single loop over n items with a fixed-size body is O(n)) on a new case, not the lesson 02 questions about range(4, 20), a 2-step body, or range(0, n, 2).")
    r.claim("help-note", "Lesson 04 says near the top that the help level went down.")
    r.claim("table", "Lesson 04 has a picture or table of the rules (single loops, nested loops, loops in a row, fixed inner loops) with none of the drill items worked out.")
    r.claim("first-item", "The first drill item in lesson 04 reuses lesson 03's example (a loop over range(5) inside a loop over range(5), or a near copy).")
    r.claim("mc-shape", "Every multiple-choice item in lesson 04 has 4 options of similar length and shape, and no option holds reasoning.")
    r.claim("accurate", "Every answer the drill implies is correct (checked by counting), and no item needs a rule the learner has not passed.")
