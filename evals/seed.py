#!/usr/bin/env python3
"""Copy a case fixture into place, filling in dates relative to today.

    seed.py <fixture dir> <dest dir> [YYYY-MM-DD]

Text files and file names may hold {{d}}, {{d+N}} or {{d-N}}: today, or N
days from today, as YYYY-MM-DD. A case's setup.sh calls this, and run.py calls it again with
the run's date to rebuild the "before" state for grading.
"""

import datetime as dt
import re
import shutil
import sys
from pathlib import Path

TOKEN = re.compile(r"\{\{d(?:([+-])(\d+))?\}\}")


def fill(text, today):
    def sub(m):
        n = int(m.group(2) or 0) * (-1 if m.group(1) == "-" else 1)
        return (today + dt.timedelta(days=n)).isoformat()

    return TOKEN.sub(sub, text)


def seed(fixture, dest, today):
    fixture, dest = Path(fixture), Path(dest)
    for src in sorted(fixture.rglob("*")):
        out = dest / fill(str(src.relative_to(fixture)), today)
        if src.is_dir():
            out.mkdir(parents=True, exist_ok=True)
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            out.write_text(fill(src.read_text(), today))
        except UnicodeDecodeError:
            shutil.copyfile(src, out)


if __name__ == "__main__":
    today = dt.date.fromisoformat(sys.argv[3]) if len(sys.argv) > 3 else dt.date.today()
    seed(sys.argv[1], sys.argv[2], today)
