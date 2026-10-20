from lib import At, Defect, grade as lint

DEFECTS = [
    Defect("renamed path sync/merge.go", [At("docs/design.md", "sync/merge.go")], ("Missing", "Stale"), r"resolve\.go"),
    Defect("link to the ADR under its old name", [At("PLAN.md", "0003-last-write-wins")], ("Missing", "Stale"),
           r"last-writer-wins"),
]


def grade(r):
    lint(r, DEFECTS)
