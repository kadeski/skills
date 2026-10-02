import re
import lib

S = "compound-interest"
F03 = f"Learning/{S}/03-compounding-year-by-year.md"

AUX = {"is", "are", "was", "were", "do", "does", "did", "can", "could", "will", "would", "should",
       "has", "have", "had", "must", "may", "might", "shall", "isn't", "aren't", "doesn't", "don't",
       "didn't", "can't", "won't", "wouldn't", "shouldn't", "hasn't", "haven't", "wasn't", "weren't"}


def yes_no(block):
    """Question sentences in an item that a yes or a no would answer."""
    text = lib.strip_code(re.sub(r"^Answer:.*$", "", block or "", flags=re.M))
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


def sections(text):
    """[(heading, body)] for each `## ` section."""
    parts = re.split(r"^## +(.*)$", text or "", flags=re.M)
    return [(parts[i].strip(), parts[i + 1]) for i in range(1, len(parts) - 1, 2)]


def prose_words(text):
    """Words in the sections between `## Your guess` and `## Questions`, without
    tables, math blocks, code or image lines. None if there is no such section."""
    secs = sections(text)
    names = [h.lower() for h, _ in secs]
    if "your guess" not in names or "questions" not in names:
        return None
    mid = secs[names.index("your guess") + 1:names.index("questions")]
    if not mid:
        return None
    body = "\n".join(b for _, b in mid)
    body = re.sub(r"^\$\$$.*?^\$\$$", "", body, flags=re.M | re.S)
    body = lib.strip_code(body)
    lines = [ln for ln in body.splitlines() if not ln.lstrip().startswith(("|", "!["))]
    return len(re.findall(r"\S+", "\n".join(lines)))


def options(text):
    return re.findall(r"^\s*(?:[-*] )?\**\(?([a-h])\)", text or "", re.M)


def grade(r):
    lib.common(r)
    r.show("notes/interest.md")
    r.show("Learning/Learner.md")
    g = lib.goal(r, S)
    t03 = r.read(F03) or ""
    st = g.status("03") or ""
    fb = {i: lib.feedback(lib.item_block(t03, f"Q{i}")) for i in (1, 2, 3)}

    # Grading and bookkeeping for 03
    r.check("03 marked passed, first try", "passed, first try" in st and "redo" not in st, st)
    r.check("You can now line in 03", re.search(r"^You can now ", t03, re.M))
    r.check("every 03 answer gets one feedback", all(lib.feedback_count(lib.item_block(t03, f"Q{i}")) == 1 for i in (1, 2, 3)))
    r.check("each 03 feedback cites the notes by point", all(re.search(r"\(notes \d", fb[i]) for i in (1, 2, 3)),
            {i: fb[i][:120] for i in (1, 2, 3)})
    r.check("Help stays 2 (02 was not a first try)", g.help == 2, g.help)
    r.check("new rule r03 due in 2 days", g.rule_next("r03") == r.d(2) and g.rule_gap("r03") == 2, g.rules.get("r03"))
    r.check("r02 not moved before it is answered", g.rule_next("r02") == r.d(0) and g.rule_gap("r02") == 2, g.rules.get("r02"))
    lm, lm0 = r.read("Learning/Learner.md") or "", r.read_before("Learning/Learner.md")
    r.check("Learner.md gains the 2-column table preference, old lines kept",
            re.search(r"\b(2|two)[ -]columns?\b", lm, re.I) and all(ln in lm for ln in lm0.splitlines() if ln.strip()), lm)
    before_guess = set((lib.section(r.read_before(F03), "Guess for next time (not graded)") or "").splitlines())
    added_guess = [ln for ln in (lib.section(t03, "Guess for next time (not graded)") or "").splitlines() if ln not in before_guess and not ln.startswith("You can now")]
    r.check("03 does not reveal its own guess", not re.search(r"\bb\)|864|1\.728|1\.2\^3|1\.2³", " ".join(added_guess), re.I), added_guess)

    new = lib.new_lessons(r, S)
    r.check("lesson 04 written and linked", len(new) == 1 and "/04-" in new[0] and "](04-" in (g.plan.get("04") or [""])[0], new)
    t04 = r.read(new[0]) if new else ""

    # Learner.md preferences, on everything the run wrote
    written = "\n".join([t04, *fb.values(), g.rules.get("r03") or "",
                         *re.findall(r"^You can now .*$", t03, re.M)])
    # Each needs lesson 04 to exist, so a run that writes nothing gets no credit.
    pics = [f for f in r.new_files() if f.endswith((".svg", ".png"))]
    r.check("no new picture files", new and not pics, pics or "no lesson 04")
    r.check("no image link in what the run wrote", new and "![" not in written, "no lesson 04" if not new else "")
    r.check("04 has a table in place of a picture", len(re.findall(r"^\|.*\|\s*$", t04, re.M)) >= 3)
    wide = [ln for ln in re.findall(r"^\|.*\|\s*$", written, re.M) if len(ln.strip().strip("|").split("|")) > 2]
    r.check("every table the run wrote has at most 2 columns", new and not wide, wide[:2] or "no lesson 04")
    r.check("no $ math in what the run wrote", new and "$" not in written, "no lesson 04" if not new else "")
    times = re.findall(r"×|\\times|\\cdot|·|\d ?\* ?\d", written)
    r.check("times written as x", new and not times, times[:5] or "no lesson 04")
    r.check("never the word principal", new and not re.search(r"principal", written, re.I),
            re.findall(r".{0,40}principal.{0,40}", written, re.I)[:3] or "no lesson 04")
    if not new:
        return

    # Concept lesson rules for 04
    heads = [h for h, _ in sections(t04)]
    r.check("04 opens with a Review section (r02 is due)", heads[:1] == ["Review"], heads)
    rev = lib.section(t04, "Review")
    r.check("Review holds one R item", rev is not None and lib.items(rev, "R") == ["1"], lib.items(rev or "", "R"))
    r1 = lib.item_block(t04, "R1") or ""
    r.check("R1, if mc, has 4 options", len(options(r1)) in (0, 4), options(r1))
    r.check("04 reveals the guess under Your guess", lib.section(t04, "Your guess") is not None, heads)
    n = prose_words(t04)
    r.check("prose between the reveal and the questions is under 120 words", n is not None and 0 < n < 120, n)
    qs = lib.items(lib.section(t04, "Questions"))
    r.check("04 has 2 or 3 questions", len(qs) in (2, 3), qs)
    yn = {q: yes_no(lib.item_block(t04, f"Q{q}")) for q in qs}
    r.check("no yes/no question", not any(yn.values()), {k: v for k, v in yn.items() if v})
    last = heads[-1] if heads else ""
    r.check("04 ends with a guess for next time (05 teaches a new idea)", last.lower().startswith("guess for next time"), heads)
    guess = lib.section(t04, last) or ""
    r.check("the guess, if mc, has 4 options", len(options(guess)) in (0, 4), options(guess))

    r.claim("reveal", "Lesson 04's Your guess section says the answer is b) 500 x 1.2^3 (864) and shows where the learner's a) 500 x 1.6 goes wrong: it adds the three 20%s instead of applying the factor 1.2 three times.")
    r.claim("problem-first", "The prose after the reveal in lesson 04 opens with a problem the growth factor solves (such as working year by year being slow over many years) before it states the rule.")
    for q in qs:
        r.claim(f"new-case-Q{q}", f"Q{q} in lesson 04's Questions uses a new case or new numbers, not the lesson's own example (500 at 20% for 3 years) or any case already worked in lesson 04.")
    r.claim("own-words", "At least one question in lesson 04's Questions section asks the learner to explain something in their own words.")
    r.claim("no-answers", "Lesson 04 does not hold the answer to any of its own questions or its review item: no table, example or reveal works one out.")
    r.claim("review-new-case", "R1 in lesson 04 tests simple interest (the same amount, rate times start, every year) on a new case, not lesson 02's items (800 at 3% for 4 years, 1500 at 4% for 2 years, 10% doubling in 5 years) or its reveal (200 at 5% for 3 years).")
    r.claim("review-shape", "R1 in lesson 04 is a number question, or a multiple-choice question whose 4 options share one shape, none longer or more detailed than the right one, with no reasoning inside an option.")
    r.claim("guess-next", "Lesson 04's Guess for next time asks about interest added more than once a year (lesson 05's idea) without teaching it first, as an mc or number question.")
    r.claim("guess-shape", "Lesson 04's Guess for next time is a number question, or a multiple-choice question whose 4 options share one shape, none longer or more detailed than the right one, with no reasoning inside an option.")
    r.claim("accurate", "Every fact in lesson 04 and in the feedback on lesson 03 matches the notes, and every number the lesson, feedback, table or options imply is correct.")
