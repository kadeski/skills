from lib import At, Defect, grade as lint

DEFECTS = [
    Defect("TBD backup owner with no issue", [At("ROADMAP.md", "nightly backup job")], ("Missing",), r"issue|ticket"),
    Defect("docs/search.md missing from the index", [At("docs/index.md", "# Docs", span=4), At("docs/search.md")],
           ("Missing",), r"search"),
]


def grade(r):
    lint(r, DEFECTS)
