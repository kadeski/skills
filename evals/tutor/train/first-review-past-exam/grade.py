import re
import lib

S = "density"
F03 = f"Learning/{S}/03-density.md"


def grade(r):
    lib.common(r)
    r.show("notes/density.md")
    g = lib.goal(r, S)
    t03 = r.read(F03)
    r.check("03 marked passed, first try", "passed, first try" in (g.status("03") or ""), g.status("03"))
    r.check("You can now line in 03", re.search(r"^You can now ", t03, re.M))
    r.check("every answer gets feedback", all(lib.feedback_count(lib.item_block(t03, f"Q{i}")) == 1 for i in (1, 2, 3)))
    r.check("Help stays 2 (02 was not a first try)", g.help == 2, g.help)
    r.check("Exam date unchanged", re.search(rf"^- Exam: {r.d(1)}$", g.text, re.M))
    # Lesson 03 may yield one rule or two (D = m / V, and size does not change it), under any id.
    before = set(lib.section(r.read_before(f"Learning/{S}/goal.md"), "Rules").splitlines())
    added = [x for x in (lib.section(g.text, "Rules") or "").splitlines() if x.startswith("- ") and x not in before and not x.startswith("- r02")]
    r.check("new rules from 03 have their first review moved to the day before the exam (today)",
            added and all(f"next {r.d(0)}" in x for x in added), added)
    r.check("r02, due on the exam day, unchanged", g.rule_next("r02") == r.d(1) and g.rule_gap("r02") == 2, g.rules.get("r02"))
    new = lib.new_lessons(r, S)
    r.check("lesson 04 written and linked", len(new) == 1 and "/04-" in new[0] and "](04-" in (g.plan.get("04") or [""])[0], new)
    if not new:
        return
    t04 = r.read(new[0])
    rev = lib.section(t04, "Review")
    want = [str(i) for i in range(1, min(len(added), 3) + 1)] or ["1"]
    r.check("04 has a Review section with one R question per new rule due today", rev is not None and lib.items(rev, "R") == want, (lib.items(rev or "", "R"), len(added)))
    r.check("04 reveals the guess", lib.section(t04, "Your guess") is not None)
    r.check("04 has 2 or 3 questions", len(lib.items(t04)) in (2, 3), lib.items(t04))
    r.claim("review-new-case", "Every review question in lesson 04 tests a rule from lesson 03 (density is mass divided by volume, or density does not depend on the size of the piece), none tests the volume of a box, and each uses a new case, not lesson 03's own items: not the 50 g, 20 cm^3 block, the 135 g, 50 cm^3 stone, the steel pieces, or the wood block and iron nail.")
