from lib import At, Defect, grade as lint

DEFECTS = [
    Defect("docs/caching.md missing from the index",
           [At("docs/README.md", "Every doc in this folder", span=5), At("docs/caching.md", "# Caching")],
           ("Missing",), r"caching"),
    Defect("moved path src/cache/memory.py", [At("docs/architecture.md", "src/cache/memory.py")],
           ("Missing", "Stale"), r"src/store/cache\.py"),
]
DECOYS = [
    At("docs/architecture.md", "A request comes in through", name="existing path src/api/routes.py"),
    At("docs/architecture.md", "src/send/sender.py", name="existing path src/send/sender.py"),
]


def grade(r):
    lint(r, DEFECTS, DECOYS)
