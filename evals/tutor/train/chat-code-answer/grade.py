import re
import lib

S = "python-sets"
F = f"cwd/{S}/02-union-and-intersection.md"
CODE = "all_tags = tags_a | tags_b\nsame_tags = {*tags_a, *tags_b}  # also works"


def fences(block):
    return [m.strip("\n") for m in re.findall(r"^```[a-z]*\n(.*?)^```", block or "", re.M | re.S)]


def grade(r):
    lib.common(r)
    r.show("notes/sets.md")
    g = lib.goal(r, S)
    t = r.read(F) or ""
    q2 = lib.item_block(t, "Q2") or ""
    answer = q2[:q2.find("> **Feedback:**")] if "> **Feedback:**" in q2 else q2
    r.check("Q2 code copied exactly inside a fenced block", CODE in fences(answer), fences(answer))
    r.check("no markdown escapes added", not re.search(r"\\[*_|]", answer), answer[:300])
    r.check("Q2 sure tag kept", re.search(r"\bsure\b", answer), answer[-120:])
    r.check("Q1 answer copied word for word",
            "Answer: blue is in both, and a set keeps each value once (sure)" in (lib.item_block(t, "Q1") or ""),
            (lib.item_block(t, "Q1") or "")[:300])
    r.check("Q3 answer copied word for word",
            "Answer: & only keeps the shared values, so it can never be bigger than |, which keeps all of them"
            in (lib.item_block(t, "Q3") or ""), (lib.item_block(t, "Q3") or "")[:300])
    r.check("each Q gets feedback", all(lib.feedback_count(lib.item_block(t, f"Q{i}")) == 1 for i in (1, 2, 3)))
    fb = lib.feedback(q2)
    r.check("a quote holding * or _ sits in a code span, not in quotation marks",
            fb and not any(re.search(r"[*_]", a + b) for a, b in re.findall(r'"([^"\n]+)"|“([^”\n]+)”', fb)),
            fb[:300])
    st = g.status("02") or ""
    r.check("plan says passed, first try", st.startswith("passed") and "first try" in st, st)
    r.check("lesson 03 written", any("/03-" in f for f in lib.new_lessons(r, S)), lib.new_lessons(r, S))

    r.claim("right", "The feedback on Q2 says the answer is right, and does not call the second line wrong or needless.")
