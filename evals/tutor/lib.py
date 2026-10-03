"""Helpers for tutor cases: parse goal.md and lessons, and the format checks
every run gets. A case's grade.py calls `common(r)` first."""

import re

EM_DASH = "\u2014"


# ---------- parsing ----------


class Goal:
    def __init__(self, text):
        self.text = text or ""
        m = re.search(r"^- Help: *(\d)", self.text, re.M)
        self.help = int(m.group(1)) if m else None
        self.plan = {}  # "02" -> (line, status or "")
        self.rules = {}  # "r02" -> line
        self.misconceptions = []
        section = None
        for line in self.text.splitlines():
            if line.startswith("## "):
                section = line[3:].strip().lower()
                continue
            if not line.startswith("- "):
                continue
            if section == "plan":
                m = re.match(r"- \[?(\d\d)\b[^\]]*\]?(?:\([^)]*\))?(?: - (.*))?$", line)
                if m:
                    self.plan[m.group(1)] = (line, (m.group(2) or "").strip())
            elif section == "rules":
                m = re.match(r"- (r\d\d)\b", line)
                if m:
                    self.rules[m.group(1)] = line
            elif section == "misconceptions":
                self.misconceptions.append(line[2:])

    def status(self, num):
        return self.plan.get(num, ("", None))[1]

    def rule_next(self, rid):
        m = re.search(r"next (\d{4}-\d\d-\d\d)", self.rules.get(rid, ""))
        return m.group(1) if m else None

    def rule_gap(self, rid):
        m = re.search(r"gap (\d+)", self.rules.get(rid, ""))
        return int(m.group(1)) if m else None

    def rule_learned(self, rid):
        return "learned" in self.rules.get(rid, "")


def goal(r, slug):
    return Goal(r.read(f"cwd/{slug}/goal.md"))


def goal_before(r, slug):
    return Goal(r.read_before(f"cwd/{slug}/goal.md"))


def lesson_files(r, slug):
    """Lesson and review files in the goal folder, by name."""
    return sorted(f for f in r.files() if re.match(rf"cwd/{slug}/(\d\d-.*|review-.*)\.md$", f))


def new_lessons(r, slug):
    return [f for f in r.new_files() if re.match(rf"cwd/{slug}/(\d\d-.*|review-.*)\.md$", f)]


def section(text, heading):
    """Body under `## heading` up to the next `## `."""
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text or "", re.M | re.S)
    return m.group(1) if m else None


def items(text, prefix="Q"):
    """Numbers of the **Q1.** style items in a text."""
    return re.findall(rf"^\*\*{prefix}(\d+)\.\*\*", text or "", re.M)


def item_block(text, label):
    """From `**Q2.**` up to the next item or heading."""
    m = re.search(rf"^\*\*{re.escape(label)}\.\*\*(.*?)(?=^\*\*[QR]\d+\.\*\*|^## |\Z)", text or "", re.M | re.S)
    return m.group(1) if m else None


def feedback(block):
    """Everything from the first feedback quote in an item block on."""
    i = (block or "").find("> **Feedback:**")
    return "" if i < 0 else block[i:]


def last_feedback(block):
    i = (block or "").rfind("> **Feedback:**")
    return "" if i < 0 else block[i:]


def feedback_count(text):
    return len(re.findall(r"^> \*\*Feedback:\*\*", text or "", re.M))


def right_and_cited(block):
    """The item's feedback calls the answer right and cites the notes by point, like "(notes 3)"."""
    fb = feedback(block)
    return bool(re.match(r"> \*\*Feedback:\*\*\s*\**(Right|Correct)\b", fb)
                and re.search(r"\([^)\n]*notes[^)\n]*\d[^)\n]*\)", fb, re.I))


def strip_code(text):
    text = re.sub(r"^(```|~~~).*?^\1", "", text, flags=re.M | re.S)
    return re.sub(r"`[^`\n]*`", "", text)


# ---------- checks every run gets ----------


def common(r):
    """Format rules from SKILL.md, applied to every file the run wrote or
    changed. They count as two items, format and pictures, so a run that does
    nothing gets little credit for them; the detail names each rule broken."""
    touched = r.new_files() + r.changed_files()
    md = {f: r.read(f) for f in touched if f.endswith(".md")}
    svg = {f: r.read(f) for f in r.new_files() if f.endswith(".svg")}
    broken = []

    def rule(name, hits):
        if hits:
            broken.append(f"{name}: {', '.join(hits)}")

    rule("em dash", [f for f, t in {**md, **svg, "final reply": r.final}.items() if EM_DASH in (t or "")])

    def scan(name, pattern, code=True):
        rule(name, [f for f, t in md.items() if re.search(pattern, strip_code(t) if code else t, re.M)])

    scan("HTML tag", r"<(?!https?://)/?[a-zA-Z][^>\n]*>")
    scan("frontmatter", r"\A---\s*$", code=False)
    scan("checkbox", r"^\s*[-*] \[[ xX]\]")
    scan("wikilink", r"\[\[")
    scan("callout", r"^> ?\[!")
    scan("mermaid", r"^```mermaid", code=False)
    scan("$$ not on its own line", r"^(?!\$\$$).*\$\$|^\$\$.+$")
    scan("math in a table", r"^\|.*\$.*\|")
    rule("lesson lacks title or Part-of line", [
        f for f, t in md.items() if re.search(r"/(\d\d-[^/]*|review-[^/]*)\.md$", f)
        and not (t.startswith("# ") and re.search(r"^Part of \[[^\]]+\]\(goal\.md\)", t, re.M))])
    links = []
    for f, t in md.items():
        base = f.rsplit("/", 1)[0]
        links += [f"{f} -> {x}" for x in re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", t) if r.read(f"{base}/{x}") is None]
    rule("broken image link", links)
    r.check("format", not broken, "; ".join(broken))

    if svg:
        bad = [f"{f.rsplit('/', 1)[-1]}: {why}" for f, t in svg.items() for ok, why in [svg_ok(t)] if not ok]
        r.check("pictures read on a phone", not bad, "; ".join(bad))


def svg_ok(t):
    num = r"([\d.]+)"
    w = re.search(rf'<svg[^>]*\swidth="{num}"', t)
    h = re.search(rf'<svg[^>]*\sheight="{num}"', t)
    vb = re.search(rf'viewBox="0 0 {num} {num}"', t)
    if not (w and h and vb):
        return False, "svg lacks width, height or a 0-origin viewBox"
    if (float(w.group(1)), float(h.group(1))) != (float(vb.group(1)), float(vb.group(2))):
        return False, "width and height differ from the viewBox"
    if float(w.group(1)) > 400:
        return False, f"width {w.group(1)} > 400"
    sizes = [float(s) for s in re.findall(r'font-size(?:="|:\s*)([\d.]+)', t)]
    if not sizes or min(sizes) < 14:
        return False, f"font sizes {sizes} (need all >= 14)"
    if not re.search(r'<rect[^>]*fill="(white|#fff|#ffffff)"', t, re.I) and "background" not in t:
        return False, "no white background"
    return True, ""
