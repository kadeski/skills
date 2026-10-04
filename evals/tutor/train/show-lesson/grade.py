import json

import lib

S = "order-of-operations"
F3 = f"cwd/{S}/03-left-to-right.html"


def tool_events(r):
    """(index, name, input) for each tool call in the trace, in order."""
    out = []
    trace = r.dir / "trace.jsonl"
    for line in trace.read_text().splitlines() if trace.exists() else []:
        ev = json.loads(line)
        if ev.get("type") != "assistant":
            continue
        for c in ev.get("message", {}).get("content", []):
            if c.get("type") == "tool_use":
                out.append((len(out), c["name"], c.get("input", {})))
    return out


def last_write(events, rel):
    """Index of the last Write or Edit of rel, or -1 if it was written some other way."""
    hits = [i for i, name, inp in events if name in ("Write", "Edit") and inp.get("file_path", "").endswith(rel)]
    return hits[-1] if hits else -1


def shown_after(events, rel):
    """True if show_lesson got the absolute path of rel after the run last wrote it."""
    w = last_write(events, rel)
    return any(
        i > w and name.endswith("__show_lesson") and inp.get("path", "").startswith("/")
        and inp["path"].endswith(f"/home/{rel}")
        for i, name, inp in events)


def grade(r):
    lib.common(r)
    g = lib.goal(r, S)
    new = lib.new_lessons(r, S)
    r.check("03 passed", (g.status("03") or "").startswith("passed"), g.status("03"))
    r.check("one new lesson, 04", len(new) == 1 and new[0].startswith(f"cwd/{S}/04-"), new)
    ev = tool_events(r)
    calls = [inp.get("path") for _, name, inp in ev if name.endswith("__show_lesson")]
    r.check("show_lesson shows 03 after grading it", shown_after(ev, F3), calls)
    r.check("show_lesson shows the new lesson after writing it", len(new) == 1 and shown_after(ev, new[0]), calls)
    r.check("final reply still gives a file:// path", "file:///" in r.final, r.final[:300])
