"""Helpers for doc-lint cases: parse the lint report in the final reply, match
it against the defects planted in the fixture, and make the checks every run
gets. A case's grade.py lists its defects and decoys and calls `grade`.

Every fixture is a small repo in `cwd/` with no git remote, so the skill runs
without an issue tracker. Paths in a case are relative to that repo. Lines are
found by searching the untouched fixture for a needle, so a fixture edit does
not break its grader."""

import re
from dataclasses import dataclass, field

REPO = "cwd/"
GROUPS = ("Wrong", "Stale", "Missing")
EXT = r"(?:md|markdown|txt|py|go|toml|json|ya?ml|sh|js|ts|cfg|ini)"
# docs/design.md:14, ~/cwd/docs/design.md:14-16, /abs/home/cwd/PLAN.md#L3
LOC = re.compile(rf"((?:[\w.~-]+/)*[\w.-]+\.{EXT})(?::L?|#L)(\d+)(?:\s?[-–]\s?L?(\d+))?")
PATH = re.compile(rf"((?:[\w.~-]+/)*[\w.-]+\.{EXT})\b")
GROUP_WORD = re.compile(r"\b(wrong|stale|missing)\b", re.I)
LIST_ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
NONE = re.compile(r"^[\s*_`]*(none|nothing|n/a|no findings?)\b", re.I)
DOC = (".md", ".markdown", ".txt", ".rst", ".adoc")


def norm(path):
    """A cited path as a repo path: drop everything up to the last `cwd/`."""
    parts = [p for p in path.split("/") if p not in ("", ".", "~")]
    if "cwd" in parts:
        parts = parts[len(parts) - parts[::-1].index("cwd"):]
    return "/".join(parts)


# ---------- the report ----------


@dataclass
class Finding:
    group: str | None
    text: str
    locs: list = field(default_factory=list)  # (path, lo, hi)

    def add(self, text):
        self.text += "\n" + text
        for m in LOC.finditer(text):
            lo = int(m.group(2))
            self.locs.append((norm(m.group(1)), lo, int(m.group(3) or lo)))


def lone_group(text, heading):
    """The group a header line names: '### Wrong (2)', '## Missing (broken links)',
    '**Stale**', '- **Missing** - open work without an issue'. A heading only has to
    start with the group word; a bold line or list item must be the word with at
    most a count, a parenthesis or a dash and a description after it."""
    words = {w.capitalize() for w in GROUP_WORD.findall(text)}
    if len(words) != 1:
        return None
    word = words.pop()
    lead = re.match(r"^[^\w]*(\w+)", text)
    if not lead or lead.group(1).capitalize() != word:
        return None
    if heading:
        return word
    rest = r"(\*\*|__)?\s*(:?\s*\d+|\(\s*\d+\s*\)|\([^)]*\))?\s*:?\s*(\*\*|__)?\s*:?\s*([-\u2013\u2014:]\s.*)?$"
    return word if re.match(rf"^[^\w]*{word}{rest}", text.strip(), re.I) else None


def parse(final):
    """Findings in the report. A group starts at a heading, bold line or list item
    that names one group; a finding is a list item, a deeper heading or a table row
    below it. Text before the first group and after a non-group heading is skipped,
    and so are notes in a group that says it has none ("None. All links resolve.")."""
    findings, group, level, base, cur, blank, empty = [], None, None, None, None, False, False

    def start(text, g):
        f = Finding(g, "")
        f.add(text)
        findings.append(f)
        return f

    for line in final.splitlines():
        s = line.strip()
        if not s:
            blank = True
            continue
        after_blank, blank = blank, False
        h = HEADING.match(s)
        item = LIST_ITEM.match(line)
        bold = re.match(r"^(\*\*|__)(.+?)(\*\*|__):?\s*(\(\d+\))?$", s)
        head_text = h.group(2) if h else (item.group(2) if item else (bold.group(0) if bold else None))
        g = lone_group(head_text, bool(h)) if head_text is not None and not LOC.search(s) else None
        if g:
            group, level, base, cur, empty = g, len(h.group(1)) if h else None, None, None, False
            continue
        if group and not cur and NONE.match(item.group(2) if item else s) and not (item and LOC.search(s)):
            empty = True
            continue
        if h:
            if group and level and len(h.group(1)) > level:
                cur = start(h.group(2), group)
            else:
                group, cur = None, None
            continue
        if bold and not LOC.search(s):
            group, cur = None, None
            continue
        if s.startswith("|"):
            cells = [c.strip(" *_`") for c in s.strip("|").split("|")]
            if all(re.fullmatch(r":?-*:?", c) for c in cells) or not PATH.search(s):
                continue  # separator, header or counts row
            row = next((c.capitalize() for c in cells if c.capitalize() in GROUPS), None)
            start(s, row or group)
            cur = None
            continue
        if item and group is not None and not empty:
            indent = len(item.group(1))
            if base is None:
                base = indent
            if indent <= base:
                cur = start(item.group(2), group)
                continue
        if cur and (line[:1].isspace() or item or not after_blank):
            cur.add(s)
        else:
            cur = None
    return findings


# ---------- planted defects ----------


@dataclass
class At:
    """A place in the fixture: a line holding `needle` (give or take `tol`, plus
    `span` lines after it), or any line of the file when there is no needle.
    Either way the report must cite a line: a bare path could be a scope list."""
    path: str
    needle: str | None = None
    span: int = 0
    tol: int = 1
    name: str = ""

    def lines(self, r):
        if self.needle is None:
            return None
        text = r.read_before(REPO + self.path)
        if text is None:
            raise ValueError(f"fixture has no {self.path}")
        for n, line in enumerate(text.splitlines(), 1):
            if self.needle in line:
                return n - self.tol, n + self.span + self.tol
        raise ValueError(f"{self.path} has no line with {self.needle!r}")


@dataclass
class Defect:
    name: str
    at: list  # At; a finding citing any of them is about this defect
    groups: tuple  # groups the finding may sit in
    fix: str = ""  # regex the finding's text must match: the right target, value or action


class Places:
    """Resolves At lines once, and matches cited paths to fixture paths. A cited
    bare file name matches only when one fixture file has that name."""

    def __init__(self, r):
        self.r = r
        self.files = [f[len(REPO):] for f in r.files(r.before) if f.startswith(REPO)]
        self.cache = {}

    def path_is(self, cited, planted):
        if cited == planted:
            return True
        if not planted.endswith("/" + cited):
            return False
        return [f for f in self.files if f == cited or f.endswith("/" + cited)] == [planted]

    def hit(self, at, path, lo, hi):
        if not self.path_is(path, at.path):
            return False
        key = id(at)
        if key not in self.cache:
            self.cache[key] = at.lines(self.r)
        span = self.cache[key]
        return span is None or (lo <= span[1] and hi >= span[0])

    def loc_hits(self, ats, path, lo, hi):
        return any(self.hit(a, path, lo, hi) for a in ats)

    def cites(self, f, ats):
        """The finding cites one of these places."""
        return any(self.loc_hits(ats, *loc) for loc in f.locs)


# ---------- checks ----------


def report_only(r):
    before = {f for f in r.files(r.before) if f.startswith(REPO)}
    after = {f for f in r.files() if f.startswith(REPO)}
    changed = [f for f in sorted(before & after) if (r.ws / f).read_bytes() != (r.before / f).read_bytes()]
    deleted = sorted(before - after)
    new_docs = [f for f in sorted(after - before) if f.endswith(DOC)]
    bad = [f"changed {f}" for f in changed] + [f"deleted {f}" for f in deleted] + [f"new {f}" for f in new_docs]
    r.check("report only: no doc changed, deleted or added", not bad, ", ".join(bad))


def opening(final, lines=8):
    return "\n".join([s for s in final.splitlines() if s.strip()][:lines])


NEG = r"(not|n't|never|without|unable to)"
NOT_CHECKED = re.compile(
    rf"issues?\b[^.\n]{{0,80}}{NEG}\s?(be(en)?\s)?(checked|verified|looked up)"
    rf"|{NEG}\s?(be(en)?\s)?(check|verif|look)\w*\b[^.\n]{{0,60}}(\bissue|#\d|still open|\bclosed)"
    r"|\bunchecked\b[^.\n]{0,60}\bissue|\bissue[^.\n]{0,60}\bunchecked"
    r"|skip\w*[^.\n]{0,60}\bissue|\bissue[^.\n]{0,60}\bskipped",
    re.I)


def no_tracker(r):
    head = opening(r.final)
    r.check("opens by saying issue state was not checked", NOT_CHECKED.search(head), head[:300])


REPORT = re.compile(r"\b(wrong|stale|missing)\b|no (findings|problems|issues found)|nothing (to fix|found)"
                    r"|\b0 findings|found no", re.I)
COUNTS = re.compile(r"\b(wrong|stale|missing)\b\W{0,6}\d+|\b\d+\W{0,6}(wrong|stale|missing)\b", re.I)


def grade(r, defects, decoys=(), history=()):
    """The checks for one run. `decoys` are At places that look wrong but are not;
    `history` lists history files (changelogs, run logs), skipped for staleness."""
    report_only(r)
    no_tracker(r)
    places = Places(r)
    for at in [a for d in defects for a in d.at] + list(decoys):
        places.hit(at, at.path, 0, 0)  # resolve every needle now, so a stale one fails the dry run
    findings = parse(r.final)
    has_report = bool(r.final.strip())

    found = {}
    for d in defects:
        found[d.name] = any(places.loc_hits(d.at, norm(m.group(1)), int(m.group(2)), int(m.group(3) or m.group(2)))
                            for m in LOC.finditer(r.final))
        r.check(f"found: {d.name}", found[d.name], "not cited at " + ", ".join(
            f"{a.path}" + (f" ({a.needle!r})" if a.needle else "") for a in d.at))

    if defects:
        about = {d.name: [f for f in findings if places.cites(f, d.at)] for d in defects}
        hits = any(about.values())
        wrong_group = [f"{d.name} in {about[d.name][0].group}" for d in defects
                       if about[d.name] and not any(f.group in d.groups for f in about[d.name])]
        # cited, but only in a note such as "these all resolve": not reported as a finding
        wrong_group += [f"{d.name} cited outside the findings" for d in defects if found[d.name] and not about[d.name]]
        r.check("found defects sit in the right group", hits and not wrong_group,
                "; ".join(wrong_group) or "no planted defect found under a group")
        bad_fix = [d.name for d in defects if d.fix and about[d.name]
                   and not any(re.search(d.fix, f.text, re.I) for f in about[d.name])]
        r.check("found defects get the right fix", hits and not bad_fix,
                ", ".join(bad_fix) or "no planted defect found under a group")
        r.check("ends with counts per group", COUNTS.search(r.final[-1500:]), r.final[-200:])

    if not defects:
        r.check("gives a lint report", REPORT.search(r.final), r.final[:200] or "no report")

    grouped = [f for f in findings if f.group]
    listed = grouped if grouped else findings
    unlocated = [f.text.strip()[:60] for f in listed if not f.locs]
    r.check("every finding has file:line", has_report and not unlocated, unlocated or "no report")

    ok = [a for d in defects for a in d.at]
    invented = [f"{p}:{lo}" for f in listed if f.locs for p, lo, hi in f.locs[:1]
                if not places.loc_hits(ok, p, lo, hi)]
    r.check("no invented findings", has_report and not invented, invented or "no report")

    for a in decoys:
        hit = [f.text.strip()[:80] for f in listed if f.locs and places.loc_hits([a], *f.locs[0])]
        r.check(f"not flagged: {a.name}", has_report and not hit, hit or "no report")
    if history:
        hit = [f.text.strip()[:80] for f in listed if f.locs and f.group in ("Wrong", "Stale", None)
               and any(places.path_is(f.locs[0][0], h) for h in history)]
        r.check("history files not flagged as stale", has_report and not hit, hit or "no report")
    return findings
