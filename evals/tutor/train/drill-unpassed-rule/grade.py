import re
import lib

S = "metric-units"
F05 = f"Learning/{S}/05-two-steps-at-once.md"

# An option line: "- a) 250 m", "a) 250 m", "- **b)** 2.5"
OPTION = re.compile(r"^\s*(?:[-*+]\s+)?\**\(?([a-eA-E])[).]\**\s+(.*)$", re.M)
# Units only lessons 06+ (area, point 6) or nobody (volume, point 7) teach
AREA = re.compile(r"\b(?:mm|cm|km|m)\}?(?:\s*\^\s*\{?[23]\b|\s*[²³]|[23]\b)|\bsquare|\bcubic|\blit(?:re|er)s?\b|\bm[lL]\b", re.I)
AREA_WORD = re.compile(AREA.pattern + r"|\barea|\bvolume", re.I)
REASONING = re.compile(r"\b(?:because|since|so|means|as it|which|that is)\b|:", re.I)


def options(block):
    return OPTION.findall(block or "")


def quotes_learner(fb, answer):
    """A quoted stretch of 6+ characters taken from the learner's answer."""
    norm = lambda x: re.sub(r"\s+", " ", x).strip().lower()
    return any(len(q) >= 6 and norm(q) in norm(answer) for q in re.findall(r'["\u201c`]([^"\u201d`\n]+)["\u201d`]', fb))


def split_guess(text):
    """The file before `## Guess for next time`, and the guess section."""
    m = re.search(r"^## Guess for next time.*$", text or "", re.M)
    return (text, None) if not m else (text[:m.start()], text[m.start():])


def grade(r):
    lib.common(r)
    r.show("notes/metric.md")
    g = lib.goal(r, S)
    before = lib.goal_before(r, S)
    t05 = r.read(F05) or ""
    st = g.status("05") or ""
    fb1 = lib.feedback(lib.item_block(t05, "R1"))
    fb2 = lib.feedback(lib.item_block(t05, "R2"))

    # grading lesson 05
    r.check("05 marked passed, not first try (Q2 tagged guess)", "passed" in st and "first try" not in st and "redo" not in st, st)
    r.check("You can now line in 05", re.search(r"^You can now ", t05, re.M))
    r.check("Q1 to Q3, R1 and R2 each get one feedback",
            all(lib.feedback_count(lib.item_block(t05, x)) == 1 for x in ("Q1", "Q2", "Q3", "R1", "R2")))
    uncited = [x for x in ("Q1", "Q2", "Q3", "R1", "R2") if not re.search(r"notes\D{0,12}\d", lib.feedback(lib.item_block(t05, x)))]
    r.check("every feedback in 05 cites the notes by point", not uncited, uncited)
    r.check("R1 and R2 feedback quote the learner's answer",
            quotes_learner(fb1, "6 x 100 = 60") and quotes_learner(fb2, "72,000, there are 100 cm in a metre so you times by 100"),
            [fb1[:150], fb2[:150]])
    r.check("R1 feedback does not give 600 cm", fb1 and not re.search(r"\b600\b|six hundred", fb1, re.I), fb1[:300])
    r.check("R2 feedback does not give 7.2 m", fb2 and not re.search(r"\b7\.2\b|\b7\.20\b", fb2), fb2[:300])
    r.check("only R2, the wrong model, is logged (R1 is a slip)", len(g.misconceptions) == len(before.misconceptions) + 1, g.misconceptions)
    r.check("r02 and r03 answered wrong: back to 1 day",
            all(g.rule_next(x) == r.d(1) and g.rule_gap(x) == 1 for x in ("r02", "r03")), [g.rules.get("r02"), g.rules.get("r03")])
    r.check("r04 not moved before it is answered", g.rules.get("r04") == before.rules.get("r04"), g.rules.get("r04"))
    r.check("new rule r05 due in 2 days", g.rule_next("r05") == r.d(2) and g.rule_gap("r05") == 2, g.rules.get("r05"))
    r.check("Help stays 2 (05 is not a first try)", g.help == 2, g.help)
    r.claim("slip-step", "The feedback on R1 in lesson 05 treats 6 x 100 = 60 as a slip: it points at that step and asks the learner to look at it again, rather than reteaching which way to convert.")
    r.claim("wm-break", "The feedback on R2 in lesson 05 shows where 'times by 100 to get metres' parts from reality, with a small picture or a two-line trace (for example how long 72,000 m would be), rather than only stating the divide rule.")
    r.claim("wm-one-question", "The feedback on R2 in lesson 05 asks exactly one question, not two questions or one question with two parts joined by 'and' or 'so'.")
    r.claim("slip-one-question", "The feedback on R1 in lesson 05 asks exactly one question, not two questions or one question with two parts joined by 'and' or 'so'.")

    # the drill
    new = lib.new_lessons(r, S)
    r.check("lesson 06 written and linked", len(new) == 1 and "/06-" in new[0] and "](06-" in (g.plan.get("06") or [""])[0], new)
    if not new:
        return
    t06 = r.read(new[0]) or ""
    body, guess = split_guess(t06)
    qs = lib.items(body)
    rev = lib.section(t06, "Review")
    rs = lib.items(rev or "", "R")
    heads = re.findall(r"^## (.+)$", t06, re.M)
    r.check("06 opens with its Review section", heads[:1] == ["Review"], heads)
    r.check("06 Review has 1 item (r04; r02 and r03 were just reset, r05 is new)", rs == ["1"], rs)
    r.check("06 has 5 or 6 drill items", len(qs) in (5, 6), qs)
    labels = [f"Q{i}" for i in qs] + [f"R{i}" for i in rs]
    blocks = {x: lib.item_block(body, x) or "" for x in labels}
    opts = {x: options(b) for x, b in blocks.items()}
    mc = [x for x in labels if opts[x]]
    bad = {x: len(o) for x, o in opts.items() if o and [k.lower() for k, _ in o] != list("abcd")}
    r.check("every mc item has exactly 4 options, a to d", not bad, bad)
    reasoning = [f"{x}: {t}" for x in mc for _, t in opts[x] if REASONING.search(t)]
    r.check("no option holds reasoning", not reasoning, reasoning[:4])
    q1 = re.sub(r"[$\\{}]", "", blocks.get("Q1", ""))
    r.check("first drill item reuses lesson 05's 2.5 km run", re.search(r"2\.5\s*(?:km|kilomet)|250[, ]?000\s*(?:cm|centimet)", q1), q1[:200])
    hits = sorted({m.group(0) for m in AREA.finditer(lib.strip_code(body))})
    r.check("nothing before the guess uses area or volume units (no passed lesson taught them)", not hits, hits)
    r.check("06 ends with a guess at area units (07 teaches a new idea)",
            guess is not None and AREA_WORD.search(guess) and len(options(guess)) in (0, 4), (guess or "")[:200])

    r.claim("table", "Lesson 06 has a picture or table of the rules from lessons 02 to 05 (multiply to go to a smaller unit; divide to go to a bigger one; 1 kg = 1000 g and 1 g = 1000 mg; multiply the factors across two steps) with none of the drill items worked out.")
    r.claim("review-r04", "R1 in lesson 06 tests r04 (mass units: 1 kg = 1000 g, 1 g = 1000 mg) on a case not used in lesson 04 (1.2 kg to g, 3600 mg to g, 1 kg is not 100 g, milligrams in 1 g).")
    r.claim("kinds", "Every Q and R item in lesson 06 is multiple choice or asks for a single number; none asks the learner to explain in words.")
    for x in mc:
        r.claim(f"shape-{x}", f"Item {x} in lesson 06 has 4 options in the same shape (for example all bare amounts in the same unit), none longer or more detailed than the others, so they cannot be told apart without the material.")
    if len(mc) >= 2:
        r.claim("letters", "Working out each multiple-choice item in lesson 06 (Q and R), the right answer does not sit at the same letter in all of them.")
    r.claim("accurate", "Every Q and R item in lesson 06 has one right answer, that answer is correct (check the arithmetic), and for multiple choice it is among the options.")
    r.claim("guess", "The guess at the end of lesson 06 asks about area units without first teaching them (it does not say the factor is squared), and a learner could reason toward any of its options.")
