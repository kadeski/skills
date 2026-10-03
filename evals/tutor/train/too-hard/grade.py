import re
import lib

S = "exponents"
F = f"cwd/{S}/04-negative-exponents.md"
# Q1: 3^-2 = 1/9. Q3: 10^-3 = 1/1000.
ANSWERS = r"\b1\s*/\s*9\b|\\frac\{1\}\{9\}|0\.1{2,}|one.ninth|\b1\s*/\s*1,?000\b|\\frac\{1\}\{1000\}|0\.001\b|thousandth"


def grade(r):
    lib.common(r)
    r.show("notes/exponents.md")
    g = lib.goal(r, S)
    before = lib.goal_before(r, S)
    t = r.read(F) or ""
    r.check("Help rises one, to 3", g.help == 3, g.help)
    r.check("nothing graded", lib.feedback_count(t) == 0, lib.feedback_count(t))
    filled = [a.strip() for a in re.findall(r"^Answer:(.*)$", t, re.M) if a.strip()]
    r.check("every answer still blank", not filled, filled)
    qs = lib.section(t, "Questions") or ""
    hit = re.search(ANSWERS, qs, re.I) or re.search(ANSWERS, r.final or "", re.I)
    r.check("Q1 and Q3 answers not given", not hit, hit.group(0) if hit else "")
    r.check("no new lesson or review file", not lib.new_lessons(r, S), lib.new_lessons(r, S))
    r.check("04 keeps no plan status (still waiting for answers)", g.status("04") == before.status("04"), g.status("04"))
    r.check("no misconception logged", g.misconceptions == before.misconceptions, g.misconceptions)
    r.check("rules unchanged", g.rules == before.rules, g.rules)
    r.claim("no-answers", "No file the run wrote or changed works out or states the answer to R1 (c), Q1 (3 to the -2 is 1/9) or Q3 (10 to the -3 is 1/1000, a small positive number), and the final reply does not either.")
    r.check("final reply names the lesson path", "04-negative-exponents" in (r.final or ""), (r.final or "")[:200])
    r.claim("reply", "The tutor's final reply is short: a line or a few short sentences.")
