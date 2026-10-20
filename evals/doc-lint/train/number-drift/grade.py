from lib import At, Defect, grade as lint

DEFECTS = [
    Defect("upload limit 50 vs 32",
           [At("README.md", "50 concurrent"), At("docs/design.md", "so the limit is 32"),
            At("config/defaults.toml", "max_uploads")],
           ("Wrong", "Stale"), r"\b32\b"),
]


def grade(r):
    lint(r, DEFECTS, history=["CHANGELOG.md"])
    for f in ("cwd/README.md", "cwd/docs/design.md", "cwd/config/defaults.toml"):
        r.show(f)
    r.claim("limit-direction", "The report says the README's limit of 50 concurrent uploads is the wrong value and 32 is right, "
            "pointing at the load test in docs/design.md or the value in config/defaults.toml as the evidence.")
