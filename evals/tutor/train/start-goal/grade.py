import re
import lib


def grade(r):
    lib.common(r)
    r.show("notes/ohms-law.md")
    goals = [f for f in r.new_files() if re.match(r"Learning/[^/]+/goal\.md$", f)]
    r.check("one goal folder with goal.md", len(goals) == 1, goals)
    if len(goals) != 1:
        return
    slug = goals[0].split("/")[1]
    g = lib.goal(r, slug)
    r.check("Help: 2", g.help == 2, g.help)
    r.check("plan has 3 to 6 lessons", 3 <= len(g.plan) <= 6, list(g.plan))
    r.check("plan links lesson 01", "01" in g.plan and "](01-" in g.plan["01"][0], g.plan.get("01"))
    r.check("Source line names the notes file", re.search(r"^- Source:.*ohms-law\.md", g.text, re.M))
    r.check("no empty Rules or Misconceptions section", "## Rules" not in g.text and "## Misconceptions" not in g.text)
    lessons = lib.lesson_files(r, slug)
    r.check("only lesson 01 written", len(lessons) == 1 and "/01-" in lessons[0], lessons)
    if not lessons:
        return
    t = r.read(lessons[0])
    r.check("01 has 2 or 3 questions", len(lib.items(t)) in (2, 3), lib.items(t))
    r.check("01 ends with a guess for next time", lib.section(t, "Guess for next time (not graded)") is not None)
    r.check("01 has no feedback yet", lib.feedback_count(t) == 0)
    r.claim("prereqs", "Each Q in lesson 01 checks something lesson 02 (the second plan entry) builds on, such as rearranging a simple product or working with units. None asks the learner to solve a series circuit, which is the goal itself.")
    r.claim("no-teaching", "Lesson 01 teaches nothing: it has no explanation section, no worked example and no statement of Ohm's law or any series rule before the questions.")
    r.claim("guess", "The guess at the end of lesson 01 is a multiple-choice or number question about the idea lesson 02 will teach, asked before it is taught.")
    r.claim("plan-order", "The plan in goal.md puts prerequisites first: Ohm's law comes before using it on a series circuit, and the plan ends at the stated goal (current and every voltage drop in a series circuit).")
    r.claim("accurate", "Every fact in goal.md and lesson 01 agrees with the notes file the learner gave, and lesson 01 contains no answer to its own questions.")
