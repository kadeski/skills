import re
import lib

S = "two-step-equations"
F = f"Learning/{S}/04-mixed-drill.md"


def answer(block):
    """The learner's answer: from `Answer:` up to the first feedback quote."""
    block = block or ""
    i = block.find("Answer:")
    j = block.find("> **Feedback:**")
    return block[i:j if j > i else len(block)] if i >= 0 else ""


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip().lower()


def quotes(fb):
    """Quoted bits of feedback: double or curly quotes, and code spans."""
    return [next(x for x in t if x) for t in re.findall(r'"([^"\n]+)"|“([^”\n]+)”|`([^`\n]+)`', fb or "")]


def quotes_answer(fb, ans):
    a = norm(ans)
    return any(len(norm(q)) >= 3 and norm(q) in a for q in quotes(fb))


def grade(r):
    lib.common(r)
    r.show("notes/equations.md")
    g = lib.goal(r, S)
    old = lib.goal_before(r, S)
    t = r.read(F) or ""
    tb = r.read_before(F) or ""
    blk = {k: lib.item_block(t, k) or "" for k in ("Q1", "Q2", "Q3", "Q4", "Q5", "R1")}
    fb = {k: lib.feedback(b) for k, b in blk.items()}
    st = g.status("04") or ""

    r.check("no new lesson or review file", not lib.new_lessons(r, S), lib.new_lessons(r, S))
    r.check("plan names exactly Q2, Q3 and Q4 to redo",
            all(q in st for q in ("Q2", "Q3", "Q4")) and not any(q in st for q in ("Q1", "Q5", "R1", "passed")), st)
    r.check("final reply names Q2, Q3 and Q4", all(q in r.final for q in ("Q2", "Q3", "Q4")), r.final[:300])
    r.check("every answer, R1 included, gets one feedback", all(lib.feedback_count(b) == 1 for b in blk.values()),
            {k: lib.feedback_count(b) for k, b in blk.items()})
    r.check("learner's answers left as written",
            all(answer(lib.item_block(tb, k)).strip() in t for k in blk), "an Answer line was changed")
    r.check("Help stays 2", g.help == 2, g.help)
    r.check("R1 wrong: r02 back to 1 day", g.rule_next("r02") == r.d(1) and g.rule_gap("r02") == 1, g.rules.get("r02"))
    r.check("r03 not moved", g.rule_next("r03") == r.d(1) and g.rule_gap("r03") == 2, g.rules.get("r03"))

    new_mis = [m for m in g.misconceptions if m not in old.misconceptions]
    r.check("Q3 wrong model logged as 04 Q3, Q2 slip and Q5 not logged",
            any(m.startswith("04 Q3") for m in new_mis) and not any(m.startswith(("04 Q2", "04 Q5")) for m in new_mis), new_mis)
    r.check("R1 wrong model logged", any(not m.startswith("04 Q") for m in new_mis), new_mis)

    r.check("Q2 feedback does not give 35 or x = 7",
            fb["Q2"] and not re.search(r"\b35\b|x\s*=\s*7\b|\bis 7\b", fb["Q2"]), fb["Q2"][:300])
    r.check("Q3 feedback does not give the fix or x = 4",
            fb["Q3"] and not re.search(r"x\s*=\s*4\b|2x\s*=\s*8\b|x\s*\+\s*3\s*=\s*7", fb["Q3"]), fb["Q3"][:300])
    r.check("Q4 feedback does not give 21",
            fb["Q4"] and not re.search(r"\b21\b|\b7\s*[x×*]\s*3\b|\b3\s*[x×*]\s*7\b", fb["Q4"]), fb["Q4"][:300])
    r.check("R1 feedback does not give 13", fb["R1"] and not re.search(r"\b13\b", fb["R1"]), fb["R1"][:300])
    r.check("Q2, Q3 and Q4 feedback quote the learner's answer",
            all(quotes_answer(fb[k], answer(blk[k])) for k in ("Q2", "Q3", "Q4")),
            {k: quotes(fb[k]) for k in ("Q2", "Q3", "Q4")})
    r.check("Q2 slip feedback asks a question", "?" in fb["Q2"], fb["Q2"][:300])
    r.check("Q1, Q4 and Q5 feedback cite the notes by point",
            all(re.search(r"notes,? (points? )?\d", fb[k]) for k in ("Q1", "Q4", "Q5")),
            {k: fb[k][:120] for k in ("Q1", "Q4", "Q5")})

    r.claim("q2-slip", "The Q2 feedback treats the answer as a slip in one step: it points at the step 48 - 13 = 25 as the place to look, does not call the method wrong, and does not say what 48 - 13 really is.")
    r.claim("q3-break", "The Q3 feedback shows where dividing only the 2x by 2 breaks, with a small picture or a two-line trace (for example, putting x = 1 back into 2x + 6 gives 8, not 14).")
    r.claim("q3-no-fix", "The Q3 feedback does not give the fix: it does not tell the learner to subtract 6 first, nor to divide the 6 and the 14 by 2 as well.")
    r.claim("q3-one-question", "The Q3 feedback asks the learner exactly one question. Two questions, or one question with two parts joined by 'and' or 'so' (such as 'what does that give, and what should you do instead?'), count as more than one. A closing instruction such as 'redo Q3' is not a question.")
    r.claim("q4-gap", "The Q4 feedback teaches that dividing is undone by multiplying both sides, worked on a different equation (not x / 3 - 2 = 5, and not one using the numbers 3, 2 and 5 together), and leaves Q4 itself for the learner to redo.")
    r.claim("q5-right", "The Q5 feedback says the answer x = 14/4 is right. It does not call it wrong, partly right or incomplete, and does not ask the learner to simplify or change it. Noting that 14/4 equals 7/2 or 3.5 is allowed.")
    r.claim("r1-break", "The R1 feedback shows where taking 9 from both sides goes wrong, with a small picture or a two-line trace (for example, putting -5 back into x - 9 gives -14, not 4), and does not tell the learner to add 9.")
    r.claim("r1-one-question", "The R1 feedback asks the learner exactly one question. Two questions, or one question with two parts joined by 'and' or 'so', count as more than one. A closing instruction is not a question.")
    r.claim("log", "The new Misconceptions line for Q3 states the learner's wrong idea in plain words (dividing only the x term by 2 and leaving the 6 alone), not the fix.")
