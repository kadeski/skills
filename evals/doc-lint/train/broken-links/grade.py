from lib import At, Defect, grade as lint

DEFECTS = [
    Defect("link to the renamed setup guide", [At("PLAN.md", "docs/setup.md")], ("Missing", "Stale"), r"install\.md"),
    Defect("anchor #rollback", [At("docs/design.md", "ops.md#rollback")], ("Missing", "Stale"), r"rolling-back"),
]
DECOYS = [
    At("PLAN.md", "#summary-format", name="working anchor #summary-format"),
    At("docs/install.md", "#running-on-a-schedule", name="working anchor #running-on-a-schedule"),
    At("docs/design.md", "parse/parse.go", name="existing path parse/parse.go"),
]


def grade(r):
    lint(r, DEFECTS, DECOYS)
