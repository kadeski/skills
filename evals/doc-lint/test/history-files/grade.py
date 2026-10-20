from lib import At, Defect, grade as lint

DEFECTS = [
    Defect("shopping list row says blocked",
           [At("PLAN.md", "| Shopping list |", tol=0), At("PLAN.md", "Unblocked")],
           ("Stale", "Wrong"), r"in progress|unblocked|#11"),
]


def grade(r):
    lint(r, DEFECTS, history=["CHANGELOG.md", f"docs/runs/{r.d(-40)}-load-test.md"])
