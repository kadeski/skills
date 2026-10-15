"""Helpers for tutor cases: parse goal.md and lesson pages, and the format
checks every run gets. A case's grade.py calls `common(r)` first.

Lesson and review pages are HTML (the Format section of SKILL.md). A page is
parsed once into a small node tree, and every query below walks it. `section`
and `item_block` return HTML, so queries compose; `text` turns HTML into plain
text for regex checks."""

import functools
import itertools
import re
import shutil
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path

EM_DASH = "\u2014"
HEAD = Path(__file__).resolve().parents[2] / "plugins/tutor/skills/tutor/head.html"
MARKER = re.search(r"<!--.*?-->", HEAD.read_text()).group(0)
LESSON = r"(\d\d-[^/]*|review-[^/]*)\.(html|md)$"

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
BLOCK = {"address", "article", "aside", "blockquote", "body", "dd", "div", "dl", "dt", "figcaption", "figure", "footer",
         "h1", "h2", "h3", "h4", "h5", "h6", "head", "header", "hr", "html", "li", "main", "nav", "ol", "p", "pre", "section",
         "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul"}
HIDDEN = {"style", "script", "title"}
NOT_PROSE = HIDDEN | {"pre", "table", "h1", "h2", "h3", "h4", "h5", "h6"}
# KaTeX auto-render's delimiters in head.html's order, and the tags it skips; title is outside body.
MATH = {"$$": "$$", "$": "$"}
NOT_MATH = {"script", "noscript", "style", "textarea", "pre", "code", "option", "title"}
# An open element of the key's tag ends where one of these tags starts.
CLOSED_BY = {"p": BLOCK, "li": {"li"}, "tr": {"tr"}, "td": {"td", "th", "tr"}, "th": {"td", "th", "tr"},
             "dt": {"dt", "dd"}, "dd": {"dt", "dd"}}


# ---------- goal.md (markdown) ----------


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


def md_section(text, heading):
    """Body under the markdown `## heading` up to the next `## `."""
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text or "", re.M | re.S)
    return m.group(1) if m else None


def lesson_files(r, slug):
    """Lesson and review files in the goal folder, by name."""
    return sorted(f for f in r.files() if re.match(rf"cwd/{slug}/{LESSON}", f))


def new_lessons(r, slug):
    return [f for f in r.new_files() if re.match(rf"cwd/{slug}/{LESSON}", f)]


# ---------- the page tree ----------


class Node:
    """An element. In the parsed text, [start:end] is the whole element and
    [inner:inner_end] what sits between its tags."""

    def __init__(self, tag, attrs, start, inner):
        self.tag, self.attrs, self.children = tag, attrs, []
        self.start, self.inner, self.inner_end, self.end = start, inner, inner, inner

    def has_class(self, name):
        return name in self.attrs.get("class", "").split()


class _Parser(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.text = text
        self.lines = [0] + [m.end() for m in re.finditer("\n", text)]
        self.root = Node(None, {}, 0, 0)
        self.stack = [self.root]
        self.feed(text)
        self.close()
        while len(self.stack) > 1:
            self._pop(len(text))
        self.root.inner_end = self.root.end = len(text)

    def _at(self):
        line, col = self.getpos()
        return self.lines[line - 1] + col

    def _pop(self, at, end=None):
        node = self.stack.pop()
        node.inner_end, node.end = at, at if end is None else end

    def handle_starttag(self, tag, attrs):
        at = self._at()
        while tag in CLOSED_BY.get(self.stack[-1].tag, ()):
            self._pop(at)
        node = Node(tag, {k: v or "" for k, v in attrs}, at, at + len(self.get_starttag_text()))
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        if not any(n.tag == tag for n in self.stack[1:]):
            return
        at = self._at()
        while self.stack[-1].tag != tag:
            self._pop(at)
        self._pop(at, self.text.find(">", at) + 1 or len(self.text))

    def handle_data(self, data):
        self.stack[-1].children.append(data)


@functools.lru_cache(maxsize=256)
def _parse(text):
    return _Parser(text).root


def _elements(node):
    for c in node.children:
        if isinstance(c, Node):
            yield c
            yield from _elements(c)


def _find(html, tag, cls=None):
    return [n for n in _elements(_parse(html or "")) if n.tag == tag and (cls is None or n.has_class(cls))]


SCRIPTS = [n.attrs for n in _find(HEAD.read_text(), "script")]


def _raw(node):
    """The node's text as written, with tags dropped and entities decoded."""
    return "".join(c if isinstance(c, str) else _raw(c) for c in node.children)


def _squash(parts):
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def _flatten(nodes, lines, cur):
    def flush():
        if line := _squash(cur):
            lines.append(line)
        cur.clear()

    for c in nodes:
        if isinstance(c, str):
            cur.append(c)
        elif c.tag in HIDDEN or c.tag == "img":
            continue
        elif c.tag == "code":
            cur.append(f"`{_raw(c)}`")
        elif c.tag == "br":
            flush()
        elif c.tag == "pre":
            flush()
            lines.extend(ln.rstrip() for ln in _raw(c).strip("\n").split("\n"))
        elif c.tag == "tr":
            flush()
            cells = [" ".join(_text(x).splitlines()) for x in c.children if isinstance(x, Node) and x.tag in ("td", "th")]
            lines.append("| " + " | ".join(cells) + " |")
        elif c.tag in BLOCK:
            flush()
            if c.tag == "li":
                cur.append("- ")
            _flatten(c.children, lines, cur)
            flush()
        else:
            _flatten(c.children, lines, cur)


def _text(node):
    lines, cur = [], []
    _flatten(node.children if node.tag is None else [node], lines, cur)
    return "\n".join(lines + [x for x in [_squash(cur)] if x])


def text(html):
    """Plain text: each block on its own lines, list items as `- `, code in
    backticks, table rows as `| a | b |`, and no pictures, styles or title."""
    return _text(_parse(html or ""))


def _prose(node):
    """The inline text of each block a learner reads as prose, outside code
    blocks, tables and headings."""
    cur = []
    for c in node.children:
        if isinstance(c, str) or c.tag not in BLOCK | NOT_PROSE:
            cur.append(c if isinstance(c, str) else _text(c))
            continue
        if line := _squash(cur):
            yield line
        cur = []
        if c.tag not in NOT_PROSE:
            yield from _prose(c)
    if line := _squash(cur):
        yield line


# ---------- page queries ----------


def sections(text):
    """[(heading, html)] for each `<h2>`, up to the next one. The part before
    the first `<h2>` comes first, with heading ""."""
    text = text or ""
    heads = _find(text, "h2")
    starts = [0] + [h.end for h in heads]
    ends = [h.start for h in heads] + [len(text)]
    return list(zip([""] + [_text(h) for h in heads], (text[s:e] for s, e in zip(starts, ends))))


def section(text, heading):
    """The HTML under `<h2>heading</h2>` up to the next `<h2>`, or None."""
    return next((html for name, html in sections(text) if name and name == heading), None)


def items(text, prefix="Q"):
    """Numbers of the `<section id="Q1">` style items, in order."""
    ids = (n.attrs.get("id", "") for n in _find(text, "section"))
    return [m.group(1) for i in ids if (m := re.fullmatch(rf"{prefix}(\d+)", i))]


def item_block(text, label):
    """The HTML inside `<section id="label">`, or None."""
    n = next((n for n in _find(text, "section") if n.attrs.get("id") == label), None)
    return None if n is None else text[n.inner:n.inner_end]


def history(block):
    """An item's answers and feedback quotes in page order, as ("answer",
    the learner's words) and ("feedback", text)."""
    out = []
    for n in _elements(_parse(block or "")):
        if n.tag == "pre" and n.has_class("answer"):
            out.append(("answer", _raw(n).strip()))
        elif n.tag == "blockquote" and n.has_class("feedback"):
            out.append(("feedback", _text(n)))
    return out


def answers(block):
    """The learner's answers, word for word, in order."""
    return [t for kind, t in history(block) if kind == "answer"]


def feedbacks(block):
    return [t for kind, t in history(block) if kind == "feedback"]


def feedback(block):
    """Every feedback quote in an item block, as text."""
    return "\n".join(feedbacks(block))


def last_feedback(block):
    """The last feedback quote and whatever follows it in the block, such as
    a picture or table placed right after the quote, as text."""
    fb = _find(block, "blockquote", "feedback")
    return text(block[fb[-1].start:]) if fb else ""


def feedback_count(text):
    return len(_find(text, "blockquote", "feedback"))


def hints(block):
    return [_text(n) for n in _find(block, "p", "hint")]


def passes(text):
    """The `You can now ...` lines."""
    return [_text(n) for n in _find(text, "p", "pass")]


def images(html):
    return [n.attrs.get("src", "") for n in _find(html, "img")]


def tables(html):
    """Each table as rows of cell texts."""
    return [[[_text(c) for c in tr.children if isinstance(c, Node) and c.tag in ("td", "th")]
             for tr in _elements(t) if tr.tag == "tr"] for t in _find(html, "table")]


def right_and_cited(block):
    """The item's feedback calls the answer right and cites the notes by point, like "(notes 3)"."""
    fb = feedback(block)
    return bool(re.match(r"(Right|Correct)\b", fb)
                and re.search(r"\([^)\n]*notes[^)\n]*\d[^)\n]*\)", fb, re.I))


def strip_code(text):
    """text without `<pre>` or `<code>` elements, fenced blocks or backtick spans."""
    text = text or ""
    kept, at = [], 0
    for n in sorted((n for n in _elements(_parse(text)) if n.tag in ("pre", "code")), key=lambda n: n.start):
        if n.start >= at:
            kept.append(text[at:n.start])
            at = n.end
    text = "".join(kept) + text[at:]
    text = re.sub(r"^(```|~~~).*?^\1", "", text, flags=re.M | re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def title(page):
    """The text of the page's `<h1>`, or None."""
    h1 = _find(page, "h1")
    return _text(h1[0]) if h1 else None


def part_of(page):
    """The page has a `Part of ...` line that links goal.md."""
    return any(_text(p).startswith("Part of")
               and any(a.tag == "a" and a.attrs.get("href") == "goal.md" for a in _elements(p))
               for p in _find(page, "p"))


def _text_runs(node):
    """Each run of text between tags, as KaTeX auto-render joins them, outside NOT_MATH."""
    for is_text, run in itertools.groupby(node.children, lambda c: isinstance(c, str)):
        if is_text:
            yield "".join(run)
        else:
            for c in run:
                if c.tag not in NOT_MATH:
                    yield from _text_runs(c)


def _math_closes(text):
    """Every math delimiter in text has its closing one, by auto-render's splitAtDelimiters."""
    left = re.compile("|".join(map(re.escape, MATH)))
    at = 0
    while m := left.search(text, at):
        right, depth, i = MATH[m.group()], 0, m.end()
        while i < len(text) and not (depth <= 0 and text.startswith(right, i)):
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 2 if text[i] == "\\" else 1
        if i >= len(text):
            return False
        at = i + len(right)
    return True


def unbalanced_math(page):
    """Some `$` or `$$` in the page's text has no closing one, so the raw TeX shows."""
    return not all(_math_closes(t) for t in _text_runs(_parse(page or "")))


def controls(page):
    """The page's script elements that are not head.html's: its control."""
    return [n for n in _find(page, "script") if n.attrs not in SCRIPTS or _raw(n).strip()]


NETWORK = re.compile(r"\bfetch\s*\(|XMLHttpRequest|WebSocket|EventSource|sendBeacon|\bimport\s*\(|importScripts|new\s+Image\b")


def _network_call(page, scripts):
    """A control script, or any `on*` attribute on the page, can reach the network."""
    handlers = (v for n in _elements(_parse(page or "")) for k, v in n.attrs.items() if k.startswith("on"))
    return any(NETWORK.search(code) for code in [*map(_raw, scripts), *handlers])


def _syntax_error(page, scripts):
    """False if every control script passes `node --check`, else why not."""
    if not scripts:
        return False
    if not shutil.which("node"):
        return "node was not found on PATH"
    with tempfile.TemporaryDirectory() as tmp:
        for i, n in enumerate(scripts):
            path = Path(tmp) / f"control{i}.js"
            path.write_text(_raw(n))
            run = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=30)
            if run.returncode:
                return run.stderr.strip().splitlines()[-1] if run.stderr.strip() else "node --check failed"
    return False


# (rule name, function of (page, control scripts) that is truthy when the page breaks it)
PAGE_RULES = [
    ("unbalanced math", lambda page, scripts: unbalanced_math(page)),
    ("script outside a concept lesson", lambda page, scripts: bool(scripts) and section(page, "Your guess") is None),
    ("more than one control script", lambda page, scripts: len(scripts) > 1),
    ("script with src not from head.html", lambda page, scripts: any("src" in n.attrs for n in scripts)),
    ("network call in a script", _network_call),
    ("control without a picture or table", lambda page, scripts: bool(scripts) and not images(page) and not tables(page)),
    ("script fails node --check", _syntax_error),
]


def control_claims(r, page, name):
    """Judge claims on a lesson's control, made only when the page has one."""
    if controls(page):
        r.claim("control-no-answers", f"The interactive control in {name} cannot be used to read off an answer to any of the lesson's questions.")
        r.claim("control-own-example", f"The interactive control in {name} works only on the lesson's own example, not on numbers the learner types in.")


# ---------- checks every run gets ----------


def common(r):
    """Format rules from SKILL.md, applied to every file the run wrote or
    changed, with the page rules in PAGE_RULES. They count as two items,
    format and pictures, so a run that does nothing gets little credit for
    them; the detail names each rule broken."""
    touched = r.new_files() + r.changed_files()
    md = {f: r.read(f) for f in touched if f.endswith(".md")}
    html = {f: r.read(f) for f in touched if f.endswith(".html")}
    md_lessons = {f: t for f, t in md.items() if re.search(rf"/{LESSON}", f)}
    pages = {f: t for f, t in html.items() if re.search(rf"/{LESSON}", f)}
    svg = {f: r.read(f) for f in r.new_files() if f.endswith(".svg")}
    broken = []

    def rule(name, hits):
        if hits:
            broken.append(f"{name}: {', '.join(hits)}")

    rule("em dash", [f for f, t in {**md, **html, **svg, "final reply": r.final}.items() if EM_DASH in (t or "")])

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
    rule("new lesson in markdown", [f for f in md_lessons if f in r.new_files()])
    rule("lesson lacks title or Part-of line", [
        f for f, t in md_lessons.items()
        if not (t.startswith("# ") and re.search(r"^Part of \[[^\]]+\]\(goal\.md\)", t, re.M))])
    rule("page lacks the head.html marker", [f for f, t in pages.items() if MARKER not in t])
    rule("page lacks h1 or Part-of line", [f for f, t in pages.items() if not (title(t) and part_of(t))])
    scripts = {f: controls(t) for f, t in pages.items()}
    for name, broke in PAGE_RULES:
        hits = []
        for f, t in pages.items():
            if found := broke(t, scripts[f]):
                hits.append(f if found is True else f"{f} ({found})")
        rule(name, hits)
    links = []
    for f, t in {**md, **pages}.items():
        base = f.rsplit("/", 1)[0]
        srcs = images(t) if f in pages else re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", t)
        links += [f"{f} -> {x}" for x in srcs if r.read(f"{base}/{x}") is None]
    rule("broken image link", links)
    long = [(f, s) for f, t in md_lessons.items() for s in md_long_sentences(t, r.read_before(f))]
    long += [(f, s) for f, t in pages.items() for s in long_sentences(t, r.read_before(f))]
    rule("sentence over 25 words", [f"{f}: {s[:60]}..." for f, s in long][:3])
    r.check("format", not broken, "; ".join(broken))

    if svg:
        bad = [f"{f.rsplit('/', 1)[-1]}: {why}" for f, t in svg.items() for ok, why in [svg_ok(t)] if not ok]
        r.check("pictures read on a phone", not bad, "; ".join(bad))


def long_sentences(page, before=None, limit=25):
    """Prose sentences over `limit` words in blocks a run added to a page.
    Skips code, tables, headings, pictures, options, the learner's answers
    and quoted words. STE100 allows 25 words in descriptive text; SKILL.md
    asks for 20."""
    old = set(_prose(_parse(before or "")))
    return _long([p for p in _prose(_parse(page or "")) if p not in old and not re.match(r"\(?[a-h]\)", p)], limit)


def md_long_sentences(text, before=None, limit=25):
    """long_sentences for a tutor 1.x markdown lesson, by line."""
    old = set((before or "").splitlines())
    text = re.sub(r"^\$\$$.*?^\$\$$", "", text or "", flags=re.M | re.S)
    text = re.sub(r"^(```|~~~).*?^\1", "", text, flags=re.M | re.S)
    paras, cur = [], []
    for line in text.splitlines():
        body = re.sub(r"^(>\s?)+", "", line).strip()
        skip = (line in old or not body or body.startswith(("#", "|", "![", "Answer:"))
                or re.match(r"([-*] |\d+\. )?\**\(?[a-h]\)", body))
        item = re.match(r"([-*]|\d+\.) ", body)
        if skip or item:
            paras.append(" ".join(cur))
            cur = []
        if not skip:
            cur.append(body)
    paras.append(" ".join(cur))
    return _long([re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", p) for p in paras], limit)


def _long(paras, limit):
    hits = []
    for p in paras:
        p = re.sub(r"`[^`]*`", "x", p)
        p = re.sub(r"\$\$.*?\$\$|\$[^$]*\$", "x", p)
        p = re.sub(r'"[^"]*"|\u201c[^\u201d]*\u201d', "x", p)
        for s in re.split(r"(?<=[.!?])\s+", p):
            if len(re.findall(r"[\w\d]+(?:['\u2019.-][\w\d]+)*", s)) > limit:
                hits.append(s)
    return hits


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
