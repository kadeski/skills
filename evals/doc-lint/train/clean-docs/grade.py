from lib import At, grade as lint

DECOYS = [
    At("docs/design.md", "~/.ledger/ledger.db", name="path in the user's home folder"),
    At("docs/design.md", "took 1.4 s", name="number measured two days ago"),
    At("PLAN.md", "docs/design.md#importing", name="working anchor #importing"),
]


def grade(r):
    lint(r, [], DECOYS, history=["CHANGELOG.md"])
