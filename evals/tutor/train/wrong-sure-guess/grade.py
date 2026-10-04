import re
import lib

S = "metric-units"
F03 = f"cwd/{S}/03-converting-lengths.html"
GUESS = "Guess for next time (not graded)"

AUX = {"is", "are", "was", "were", "do", "does", "did", "can", "could", "will", "would", "should",
       "has", "have", "had", "must", "may", "might", "shall", "isn't", "aren't", "doesn't", "don't",
       "didn't", "can't", "won't", "wouldn't", "shouldn't", "hasn't", "haven't", "wasn't", "weren't"}


def yes_no(block):
    """Question sentences in an item that a yes or a no would answer."""
    text = lib.text(lib.strip_code(block))
    hits = []
    for s in re.split(r"(?<=[.!?:])\s+|\n", text):
        s = s.strip().strip("*_ ").strip()
        if not s.endswith("?"):
            continue
        low = s.lower()
        first = (low.split() or [""])[0]
        if "true or false" in low or (first in AUX and " or " not in low):
            hits.append(s)
    return hits


def prose_words(text):
    """Words in the sections between Your guess and Questions, without
    tables, code or pictures. None if there is no such section."""
    secs = lib.sections(text)[1:]
    names = [h.lower() for h, _ in secs]
    if "your guess" not in names or "questions" not in names:
        return None
    mid = secs[names.index("your guess") + 1:names.index("questions")]
    if not mid:
        return None
    body = "\n".join(lib.text(lib.strip_code(b)) for _, b in mid)
    lines = [ln for ln in body.splitlines() if not ln.lstrip().startswith("|")]
    return len(re.findall(r"\S+", "\n".join(lines)))


def options(block):
    return re.findall(r"^\s*(?:[-*] )?\**\(?([a-h])\)", lib.text(block), re.M)


def grade(r):
    lib.common(r)
    r.show("notes/metric-units.md")
    g = lib.goal(r, S)
    t03 = r.read(F03) or ""
    st = g.status("03") or ""

    # 03: graded and passed; the guess is not graded and does not block
    r.check("03 marked passed, first try", "passed, first try" in st and "redo" not in st, st)
    r.check("You can now line in 03", any(p.startswith("You can now ") for p in lib.passes(t03)))
    r.check("every 03 answer gets one feedback", all(lib.feedback_count(lib.item_block(t03, f"Q{i}")) == 1 for i in (1, 2, 3)))
    r.check("each 03 feedback cites the notes by point",
            all(re.search(r"\(notes \d", lib.feedback(lib.item_block(t03, f"Q{i}"))) for i in (1, 2, 3)))
    before_guess = set(lib.text(lib.section(r.read_before(F03), GUESS)).splitlines())
    added_guess = [ln for ln in lib.text(lib.section(t03, GUESS)).splitlines() if ln not in before_guess and not ln.startswith("You can now")]
    r.check("03 does not reveal its own guess", not re.search(r"\bb\)|10,000|10000|10 000", " ".join(added_guess), re.I), added_guess)

    # goal.md bookkeeping
    logged = [m for m in g.misconceptions if re.match(r"03 guess\b", m)]
    r.check("wrong sure guess logged as 03 guess", len(logged) == 1, g.misconceptions)
    r.check("no misconception numbered 04 or 03 Q", not any(re.match(r"04\b|03 Q", m) for m in g.misconceptions), g.misconceptions)
    r.check("Help drops to 1 (02 and 03 first try)", g.help == 1, g.help)
    r.check("new rule r03 due in 2 days", g.rule_next("r03") == r.d(2) and g.rule_gap("r03") == 2, g.rules.get("r03"))
    r.check("r02 not due, unchanged", g.rule_next("r02") == r.d(1) and g.rule_gap("r02") == 2, g.rules.get("r02"))

    new = lib.new_lessons(r, S)
    r.check("lesson 04 written and linked", len(new) == 1 and "/04-" in new[0] and "](04-" in (g.plan.get("04") or [""])[0], new)
    if not new:
        return
    t04 = r.read(new[0]) or ""
    heads = [h for h, _ in lib.sections(t04) if h]
    head = lib.text(lib.sections(t04)[0][1])
    r.check("04 mentions Help before its first section", re.search(r"\bhelp\b", head, re.I), head[:300])
    r.check("04 has no Review section (r02 not due)", "Review" not in heads, heads)
    reveal = lib.section(t04, "Your guess")
    r.check("04 reveals 10,000 under Your guess", reveal is not None and re.search(r"10,000|10000|10 000", lib.text(reveal)), heads)
    r.check("04 has a picture in img/ numbered 04", any(re.fullmatch(r"img/04-[^/]*\.svg", s) for s in lib.images(t04)), lib.images(t04))
    n = prose_words(t04)
    r.check("prose between the reveal and the questions is under 120 words", n is not None and 0 < n < 120, n)
    qs = lib.items(lib.section(t04, "Questions"))
    r.check("04 has 2 or 3 questions", len(qs) in (2, 3), qs)
    yn = {q: yes_no(lib.item_block(t04, f"Q{q}")) for q in qs}
    r.check("no yes/no question", not any(yn.values()), {k: v for k, v in yn.items() if v})
    last = heads[-1] if heads else ""
    r.check("04 ends with a guess for next time (05 teaches a new idea)", last.lower().startswith("guess for next time"), heads)
    guess = lib.section(t04, last)
    r.check("the guess, if mc, has 4 options", len(options(guess)) in (0, 4), options(guess))
    before = lib.text("".join(b for _, b in lib.sections(t04)[:-1]) if last.lower().startswith("guess") else t04)
    vol = re.findall(r".{0,30}(?:³|\^3|cubic|cube|litre|liter|\bml\b|\b[cm]?m3\b).{0,30}", before, re.I)
    r.check("no volume taught or tested before the guess", not vol, vol[:3])

    r.claim("help-note", "Near the top of lesson 04, before the guess reveal, a line says the help level went down (not up).")
    r.claim("reveal", "Lesson 04's Your guess section says the answer is b) 10,000 and shows where the learner's a) 100 goes wrong: 100 converts only one side, but a 1 m square is 100 cm by 100 cm.")
    r.claim("logged", "The new Misconceptions line starting 03 guess says the learner thinks an area converts by the length factor (1 m² = 100 cm²).")
    r.claim("problem-first", "The prose after the reveal in lesson 04 opens with a problem the idea solves (such as why the length factor gives the wrong area) before it states the rule.")
    for q in qs:
        r.claim(f"new-case-Q{q}", f"Q{q} in lesson 04's Questions uses a new case or new numbers, not the lesson's own example (a 1 m square, 1 m² to cm²) or any case already worked in lesson 04.")
    r.claim("own-words", "At least one question in lesson 04's Questions section asks the learner to explain something in their own words.")
    r.claim("no-answers", "Lesson 04 does not hold the answer to any of its own questions: no picture, table, example or reveal works one out.")
    r.claim("picture", "Lesson 04's picture is drawn with the lesson's real numbers, such as a 1 m square split into 100 cm by 100 cm.")
    r.claim("guess-next", "Lesson 04's Guess for next time asks about volume units (lesson 05's idea) as an mc or number question.")
    r.claim("guess-shape", "Lesson 04's Guess for next time is a number question, or a multiple-choice question whose 4 options share one shape, none longer or more detailed than the right one, with no reasoning inside an option.")
    r.claim("accurate", "Every fact in lesson 04 and in the feedback on lesson 03 matches the notes, and every number the lesson, picture, feedback or options imply is correct.")
    lib.control_claims(r, t04, "lesson 04")
