import re
import lib

S = "lines"
F03 = f"cwd/{S}/03-slope-from-two-points.md"


def grade(r):
    lib.common(r)
    r.show("notes/lines.md")
    g = lib.goal(r, S)
    before = lib.goal_before(r, S)
    t03 = r.read(F03) or ""
    r.check("03 marked passed, first try", "passed, first try" in (g.status("03") or ""), g.status("03"))
    r.check("02 status unchanged", g.status("02") == before.status("02"), g.status("02"))
    r.check("You can now line in 03", re.search(r"^You can now ", t03, re.M))
    r.check("every answer gets feedback", all(lib.feedback_count(lib.item_block(t03, f"Q{i}")) == 1 for i in (1, 2, 3)))
    r.check("no harder questions added to 03", lib.items(t03) == ["1", "2", "3"], lib.items(t03))
    r.check("Help drops one, to 2", g.help == 2, g.help)
    r.check("new rule r03 due in 2 days", g.rule_next("r03") == r.d(2) and g.rule_gap("r03") == 2, g.rules.get("r03"))
    r.check("r02 not due, unchanged", g.rules.get("r02") == before.rules.get("r02"), g.rules.get("r02"))
    new = lib.new_lessons(r, S)
    r.check("lesson 04 written and linked", len(new) == 1 and "/04-" in new[0] and "](04-" in (g.plan.get("04") or [""])[0], new)
    r.check("final reply names lesson 04", "04-" in r.final, r.final[:200])
    if not new:
        return
    t04 = r.read(new[0]) or ""
    head = t04.split("\n## ", 1)[0]
    r.check("04 mentions Help before its first section", re.search(r"\bhelp\b", head, re.I), head[:300])
    r.check("04 reveals the guess", lib.section(t04, "Your guess") is not None)
    r.check("04 has no Review section (r02 not due)", lib.section(t04, "Review") is None)
    r.claim("help-note", "Near the top of lesson 04, before the guess reveal, a line says the help level went down (not up).")
    r.claim("reveal", "Lesson 04's Your guess section says the answer is a) 4 (10 = 2 x 3 + b, so b = 4) and explains where the learner's c) 16 went wrong.")
    r.claim("concept", "Lesson 04 teaches finding b from the slope and one point (notes 4), and its 2 or 3 questions use new numbers, not y = 2x + b through (3, 10). At least one asks for the learner's own words, and none is yes/no.")
    r.claim("one-name", "Each term in lesson 04 keeps one name throughout: the lesson never switches to a different word for the same thing.")
    r.claim("accurate", "Every fact in lesson 04 and the feedback in lesson 03 matches the notes, and every number the questions or feedback imply is correct.")
