from lib import At, Defect, grade as lint

DEFECTS = [
    Defect("status row for phase 2 out of date",
           [At("PLAN.md", "| 2. Search |", tol=0), At("PLAN.md", "which closed #14")],
           ("Stale", "Wrong"), r"\bdone\b|shipped|complete"),
    Defect("open export decision with no issue", [At("PLAN.md", "archived books")], ("Missing",), r"issue|ticket"),
]
DECOYS = [
    At("docs/design.md", "PLAN.md#2-search", name="working anchor #2-search"),
]


def grade(r):
    lint(r, DEFECTS, DECOYS)
    r.show("cwd/PLAN.md")
    r.claim("status-direction", "The report treats the PLAN.md status table row for phase 2 (Search) as the out-of-date part, "
            "because the phase 2 section says it is done, and does not suggest changing the section to match the table.")
