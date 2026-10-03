import re
import lib

S = "lines"
F03 = f"cwd/{S}/03-slope-from-two-points.md"


def md_item(text, label):
    """A 1.x markdown item: from `**Q2.**` up to the next item or heading."""
    m = re.search(rf"^\*\*{re.escape(label)}\.\*\*(.*?)(?=^\*\*[QR]\d+\.\*\*|^## |\Z)", text or "", re.M | re.S)
    return m.group(1) if m else ""


def md_feedback_count(text):
    return len(re.findall(r"^> \*\*Feedback:\*\*", text or "", re.M))


def grade(r):
    lib.common(r)
    r.show("notes/lines.md")
    g = lib.goal(r, S)
    t03 = r.read(F03) or ""
    st = g.status("03") or ""
    r.check("03 stays .md, with no HTML copy",
            F03 in r.changed_files() and not any("/03-" in f for f in lib.new_lessons(r, S)), lib.new_lessons(r, S))
    r.check("each 03 answer gets one markdown feedback quote",
            all(md_feedback_count(md_item(t03, f"Q{i}")) == 1 for i in (1, 2, 3)),
            [md_feedback_count(md_item(t03, f"Q{i}")) for i in (1, 2, 3)])
    r.check("You can now line in 03, in markdown", re.search(r"^You can now ", t03, re.M))
    r.check("03 marked passed, first try", "passed, first try" in st, st)
    r.check("plan still links 03 as .md", "](03-slope-from-two-points.md)" in (g.plan.get("03") or [""])[0], g.plan.get("03"))
    r.check("01 and 02 left as they are",
            all(r.read(f"cwd/{S}/{f}") == r.read_before(f"cwd/{S}/{f}")
                for f in ("01-where-youre-at.md", "02-slope-as-rise-over-run.md")))
    new = lib.new_lessons(r, S)
    r.check("one new lesson, 04, as an HTML page", len(new) == 1 and re.search(r"/04-[^/]*\.html$", new[0]), new)
    r.check("plan links 04 as .html", re.search(r"\]\(04-[^)]*\.html\)", (g.plan.get("04") or [""])[0]), g.plan.get("04"))
    if not new:
        return
    t04 = r.read(new[0]) or ""
    r.check("04 starts from head.html, with a title and the goal link",
            lib.MARKER in t04 and lib.title(t04) and lib.part_of(t04), lib.text(t04)[:200])
