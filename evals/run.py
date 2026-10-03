#!/usr/bin/env python3
"""Run a skill's eval cases, grade every run, and compare versions.

    evals/run.py run <skill> [--split train|test|all] [--runs N] [--case GLOB]
    evals/run.py dry <skill>               grade the untouched fixtures (no agent, no judge)
    evals/run.py rejudge <results dir>     judge saved runs again, report flips
    evals/run.py compare <old results dir> <new results dir>

`claude plugin eval` runs each case in a clean home (no user CLAUDE.md,
memory or other plugins). This script then grades what the run left behind:
each case's grade.py makes programmatic checks and writes claims, and an LLM
judge rules on each claim. See evals/README.md.
"""

import argparse
import datetime as dt
import fnmatch
import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"
sys.path.insert(0, str(EVALS))
from seed import seed  # noqa: E402

JUDGE_SYSTEM = """You grade one run of an AI tutor skill. You get the learner's \
message, the tutor's final reply, and every file the run created or changed \
(changed files show the before and after). Rule on each claim from this \
evidence alone. A claim passes only if the evidence clearly shows it is true; \
if it is unclear or missing, it fails. Give a one-sentence reason that points \
at the evidence."""

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "pass": {"type": "boolean"},
                    "reason": {"type": "string"},
                },
                "required": ["id", "pass", "reason"],
            },
        }
    },
    "required": ["verdicts"],
}


# ---------- one graded run ----------


class Run:
    """What grade.py sees: the run's files before and after, and its reply."""

    def __init__(self, case_dir, run_dir, today):
        self.case_dir = Path(case_dir)
        self.dir = Path(run_dir)
        self.ws = self.dir / "home"
        self.before = self.dir / "before"
        self.today = today
        self.prompt = case_prompt(self.case_dir)
        self.final = final_message(self.dir / "trace.jsonl")
        self.checks = []
        self.claims = []
        self.shown = []

    def d(self, n=0):
        return (self.today + dt.timedelta(days=n)).isoformat()

    def read(self, rel):
        p = self.ws / rel
        return p.read_text() if p.is_file() else None

    def read_before(self, rel):
        p = self.before / rel
        return p.read_text() if p.is_file() else None

    def files(self, root=None):
        base = self.ws if root is None else root
        return sorted(
            str(p.relative_to(base))
            for p in base.rglob("*")
            if p.is_file() and not any(part.startswith(".") for part in p.relative_to(base).parts)
        )

    def new_files(self):
        old = set(self.files(self.before))
        return [f for f in self.files() if f not in old]

    def changed_files(self):
        old = set(self.files(self.before))
        return [f for f in self.files() if f in old and (self.ws / f).read_bytes() != (self.before / f).read_bytes()]

    def check(self, name, ok, detail=""):
        self.checks.append({"name": name, "pass": bool(ok), "detail": "" if ok else str(detail)})

    def claim(self, cid, text):
        self.claims.append({"id": cid, "text": text})

    def show(self, rel):
        """Give the judge an unchanged file too, such as the learner's source notes."""
        self.shown.append(rel)

    def evidence(self):
        parts = [f"## Learner's message\n\n{self.prompt}", f"## Tutor's final reply\n\n{self.final}"]
        for f in self.new_files():
            if f.endswith((".md", ".svg", ".txt")):
                parts.append(f"## New file: {f}\n\n````\n{self.read(f)}\n````")
        for f in self.changed_files():
            parts.append(
                f"## Changed file: {f}\n\n### Before\n\n````\n{self.read_before(f)}\n````"
                f"\n\n### After\n\n````\n{self.read(f)}\n````"
            )
        if not self.new_files() and not self.changed_files():
            parts.append("## Files\n\nThe run created and changed no files.")
        for f in self.shown:
            parts.append(f"## Reference file (unchanged by the run): {f}\n\n````\n{self.read(f)}\n````")
        return "\n\n".join(parts)


def case_prompt(case_dir):
    p = case_dir / "prompt.md"
    if p.exists():
        return p.read_text().split("---", 2)[-1].strip()
    return simple_yaml_prompt(case_dir / "case.yaml")


def simple_yaml_prompt(path):
    for line in path.read_text().splitlines():
        s = line.strip()
        if s.startswith("prompt:"):
            return json.loads(s[len("prompt:"):].strip())
    return ""


def final_message(trace):
    text = ""
    if not trace.exists():
        return text
    for line in trace.read_text().splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "result" and isinstance(ev.get("result"), str):
            return ev["result"]
        if ev.get("type") == "assistant":
            for c in ev.get("message", {}).get("content", []):
                if c.get("type") == "text":
                    text = c["text"]
    return text


def load_grader(case_dir):
    spec = importlib.util.spec_from_file_location(f"grade_{case_dir.name}", case_dir / "grade.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(case_dir.parent.parent))  # the skill dir, for its lib.py
    spec.loader.exec_module(mod)
    return mod


def judge(run, model):
    if not run.claims:
        return [], 0
    claims = "\n".join(f"- {c['id']}: {c['text']}" for c in run.claims)
    prompt = f"{run.evidence()}\n\n# Claims to rule on\n\n{claims}\n"
    with tempfile.TemporaryDirectory() as cwd:
        out = subprocess.run(
            ["claude", "-p", "--model", model, "--tools", "", "--no-session-persistence",
             "--strict-mcp-config", "--setting-sources", "", "--disable-slash-commands",
             "--system-prompt", JUDGE_SYSTEM, "--json-schema", json.dumps(JUDGE_SCHEMA),
             "--output-format", "json"],
            input=prompt, capture_output=True, text=True, cwd=cwd, timeout=600,
        )
    res = json.loads(out.stdout)
    got = {v["id"]: v for v in (res.get("structured_output") or {}).get("verdicts", [])}
    return [
        {"id": c["id"], "text": c["text"], "pass": bool(got.get(c["id"], {}).get("pass")),
         "reason": got.get(c["id"], {}).get("reason", "judge gave no verdict")}
        for c in run.claims
    ], res.get("total_cost_usd", 0)


def grade_run(case_dir, run_dir, today, judge_model):
    run = Run(case_dir, run_dir, today)
    load_grader(case_dir).grade(run)
    verdicts, cost = judge(run, judge_model)
    items = run.checks + verdicts
    score = sum(i["pass"] for i in items) / len(items) if items else 0.0
    grades = {"score": score, "checks": run.checks, "claims": verdicts, "judge_cost_usd": cost}
    (Path(run_dir) / "grades.json").write_text(json.dumps(grades, indent=2))
    return grades


# ---------- running the suite ----------


def find_cases(skill, split):
    splits = ["train", "test"] if split == "all" else [split]
    return {s: sorted(p.parent for p in (EVALS / skill / s).glob("*/case.yaml")) for s in splits}


def open_kept(trace_path):
    """`--keep-temp` leaves <tmp>/out/trace.jsonl and seals <tmp>/sealed/home.
    Run as root, it cannot seal, and leaves the home at <tmp>/home."""
    tmp = Path(trace_path).parent.parent
    sealed = tmp / "sealed"
    if not sealed.exists() and os.geteuid() == 0 and (tmp / "home").is_dir():
        sealed = tmp
    if not sealed.exists():
        raise RuntimeError(f"kept temp layout changed: no {sealed}")
    os.chmod(tmp, 0o700)
    os.chmod(sealed, 0o700)
    home = sealed / "home"
    if not home.is_dir():
        raise RuntimeError(f"kept temp layout changed: no {home}")
    return tmp, home


def remove_tree(path):
    for p in [path, *path.rglob("*")]:
        try:
            os.chmod(p, 0o700, follow_symlinks=False)
        except OSError:
            pass
    shutil.rmtree(path, ignore_errors=True)


def local_date(iso):
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone().date()


def stats(case_scores):
    """Mean of case means, and the run-to-run noise on that mean (1 SE)."""
    means, var = [], 0.0
    for scores in case_scores.values():
        if not scores:
            continue
        m = sum(scores) / len(scores)
        means.append(m)
        if len(scores) > 1:
            var += sum((s - m) ** 2 for s in scores) / (len(scores) - 1) / len(scores)
    if not means:
        return {"mean": None, "se": None, "n_cases": 0}
    n = len(means)
    return {"mean": sum(means) / n, "se": math.sqrt(var) / n, "n_cases": n}


def skill_dir(skill):
    """The skill's folder, plugins/<plugin>/skills/<skill>."""
    found = sorted(ROOT.glob(f"plugins/*/skills/{skill}/SKILL.md"))
    if len(found) != 1:
        sys.exit(f"expected one plugins/*/skills/{skill}/SKILL.md, found {len(found)}")
    return found[0].parent


def stage_plugin(skill, dest):
    """Copy the skill's plugin into dest with evals/ added, since `claude plugin eval`
    reads cases from below the plugin and evals/ does not ship in plugins/."""
    plugin = skill_dir(skill).parent.parent
    shutil.copytree(plugin, dest)
    shutil.copytree(EVALS / skill, dest / "evals" / skill, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(EVALS / "seed.py", dest / "evals" / "seed.py")
    return dest


def skill_fingerprint(skill):
    sdir = skill_dir(skill)
    text = (sdir / "SKILL.md").read_bytes()
    rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", str(sdir.relative_to(ROOT))], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    return {"commit": rev, "skill_dirty": bool(dirty), "skill_sha256": hashlib.sha256(text).hexdigest()[:12]}


def cmd_run(a):
    cases = find_cases(a.skill, a.split)
    if a.case:
        cases = {s: [c for c in cs if fnmatch.fnmatch(c.name, a.case)] for s, cs in cases.items()}
    if not any(cases.values()):
        sys.exit("no cases matched")
    stamp = dt.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    out = EVALS / "results" / f"{a.skill}-{stamp}"
    n = 1
    while True:  # two runs started in the same second get -2, -3, ...
        try:
            out.mkdir(parents=True)
            break
        except FileExistsError:
            n += 1
            out = EVALS / "results" / f"{a.skill}-{stamp}-{n}"
    fingerprint = skill_fingerprint(a.skill)  # before the run, in case the skill changes during it
    split_of = {c.name: s for s, cs in cases.items() for c in cs}
    dirs = {c.name: c for cs in cases.values() for c in cs}

    staged = Path(tempfile.mkdtemp(prefix=f"{a.skill}-plugin-")) / "plugin"
    stage_plugin(a.skill, staged)
    cmd = ["claude", "plugin", "eval", str(staged), "--scaffold", "--keep-temp", "--trust-plugin",
           "--ablation", "none", "--no-publish", "--model", a.model, "--runs", str(a.runs),
           "-j", str(a.concurrency), "--allow-tools", "Write(~/**)", "Edit(~/**)", "Bash",
           "--output-dir", str(out / "plugin-eval"), "--json", str(out / "plugin-eval.json")]
    cmd += ["--tag", *(f"{a.skill}-{s}" for s in cases)]
    if a.case:
        cmd += ["--case", a.case]
    if a.max_cost:
        cmd += ["--max-cost-usd", str(a.max_cost)]
    print(f"Running {len(dirs)} case(s) x {a.runs} on {a.model} -> {out.relative_to(ROOT)}", flush=True)
    try:
        proc = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.DEVNULL if a.quiet else None)
    finally:
        shutil.rmtree(staged.parent)
    if not (out / "plugin-eval.json").exists():
        sys.exit(f"claude plugin eval failed (exit {proc.returncode}) and wrote no result")
    result = json.loads((out / "plugin-eval.json").read_text())
    if not result.get("cases"):
        sys.exit("claude plugin eval ran no cases; see its output above")

    jobs = []
    for case in result["cases"]:
        name = case["name"]
        if name not in dirs:
            continue
        for i, r in enumerate(case["arms"]["with"], 1):
            run_dir = out / split_of[name] / name / f"run{i}"
            run_dir.mkdir(parents=True)
            meta = {k: r.get(k) for k in ("error", "costUsd", "durationSeconds", "turns", "startedAt")}
            meta["native_graders"] = r.get("graders", [])
            tp = r.get("tracePath")
            try:
                if not tp:
                    raise RuntimeError("no tracePath")
                tmp, home = open_kept(tp)
                shutil.copyfile(tp, run_dir / "trace.jsonl")
                denied = (run_dir / "trace.jsonl").read_text().count("has been denied")
                if denied:  # the harness blocked the skill, so the run says nothing about it
                    meta["error"] = meta["error"] or f"{denied} tool call(s) denied by the harness"
                shutil.copytree(home, run_dir / "home", symlinks=True,
                                ignore=lambda d, names: [n for n in names if n.startswith(".")])
                remove_tree(tmp)
            except Exception as e:  # noqa: BLE001
                meta["error"] = meta["error"] or f"workspace: {e}"
            today = local_date(r["startedAt"])
            meta["today"] = today.isoformat()
            seed(dirs[name] / "fixture", run_dir / "before", today)
            (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))
            jobs.append((name, run_dir, today, meta))

    def work(job):
        name, run_dir, today, meta = job
        if meta["error"]:
            return name, None
        try:
            return name, grade_run(dirs[name], run_dir, today, a.judge_model)
        except Exception as e:  # noqa: BLE001
            meta["error"] = f"grading: {e}"
            (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))
            return name, None

    with ThreadPoolExecutor(max_workers=4) as pool:
        graded = list(pool.map(work, jobs))

    summary = {"skill": a.skill, "model": a.model, "judge_model": a.judge_model, "runs": a.runs,
               "fingerprint": fingerprint, "agent_cost_usd": result.get("costUsd"),
               "splits": {}}
    for split, cs in cases.items():
        per_case = {c.name: [g["score"] for n, g in graded if n == c.name and g] for c in cs}
        errors = {c.name: sum(1 for n, g in graded if n == c.name and not g) for c in cs}
        summary["splits"][split] = {"cases": per_case, "errors": errors, **stats(per_case)}
    summary["judge_cost_usd"] = sum(g["judge_cost_usd"] for _, g in graded if g)
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print_summary(out, summary)


def fmt(m, se):
    return "n/a" if m is None else f"{m:.3f} +/- {1.96 * se:.3f}"


def print_summary(out, s):
    print(f"\nResults: {out.relative_to(ROOT)}  (skill {s['fingerprint']['skill_sha256']}"
          f"{' dirty' if s['fingerprint']['skill_dirty'] else ''} @ {s['fingerprint']['commit']})")
    for split, d in s["splits"].items():
        print(f"\n{split}: {fmt(d['mean'], d['se'])}  ({d['n_cases']} cases, 95% run-noise band)")
        if split != "train":
            continue  # test scores stay aggregate so nobody tunes to them
        for name, scores in d["cases"].items():
            err = d["errors"].get(name)
            row = " ".join(f"{x:.2f}" for x in scores)
            print(f"  {name:32} {row}{f'  ({err} errored)' if err else ''}")
        fails = {}
        for g in (out / "train").glob("*/run*/grades.json"):
            case = g.parent.parent.name
            for item in json.loads(g.read_text())["checks"] + json.loads(g.read_text())["claims"]:
                if not item["pass"]:
                    key = (case, item.get("name") or item.get("id"))
                    fails[key] = fails.get(key, 0) + 1
        if fails:
            print("  most common misses:")
            for (case, item), n in sorted(fails.items(), key=lambda kv: -kv[1])[:12]:
                print(f"    {n}x {case}: {item}")
    errs = sum(sum(d["errors"].values()) for d in s["splits"].values())
    if errs:
        print(f"\n{errs} run(s) errored and are left out of the scores; see meta.json in each run folder.")
    print(f"\nCost: agent ${s['agent_cost_usd'] or 0:.2f}, judge ${s['judge_cost_usd']:.2f}")


# ---------- rejudge and compare ----------


def cmd_rejudge(a):
    out = Path(a.results).resolve()
    s = json.loads((out / "summary.json").read_text())
    jobs = []
    for split in s["splits"]:
        for run_dir in sorted((out / split).glob("*/run*")):
            if (run_dir / "grades.json").exists():
                jobs.append(run_dir)

    def work(run_dir):
        case_dir = EVALS / s["skill"] / run_dir.parent.parent.name / run_dir.parent.name
        today = dt.date.fromisoformat(json.loads((run_dir / "meta.json").read_text())["today"])
        run = Run(case_dir, run_dir, today)
        load_grader(case_dir).grade(run)
        old = {c["id"]: c["pass"] for c in json.loads((run_dir / "grades.json").read_text())["claims"]}
        new, _ = judge(run, a.judge_model or s["judge_model"])
        split = run_dir.parent.parent.name
        return [(split, run_dir.parent.name, v["id"], old.get(v["id"]), v["pass"], v["reason"]) for v in new]

    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = [r for rs in pool.map(work, jobs) for r in rs]
    flips = [r for r in rows if r[3] is not None and r[3] != r[4]]
    print(f"{len(flips)} of {len(rows)} claim verdicts flipped on a second judging.")
    for split, case, cid, old, new, reason in flips:
        if split == "train":  # test details stay hidden, like test scores
            print(f"  {case} {cid}: {old} -> {new}  ({reason})")
    hidden = sum(1 for f in flips if f[0] != "train")
    if hidden:
        print(f"  plus {hidden} flip(s) in test cases, not shown")


def cmd_dry(a):
    """A run that changed nothing should fail most checks, and no grader should crash."""
    today = dt.date.today()
    for split, cs in find_cases(a.skill, "all").items():
        for case_dir in cs:
            with tempfile.TemporaryDirectory() as tmp:
                run_dir = Path(tmp)
                seed(case_dir / "fixture", run_dir / "home", today)
                seed(case_dir / "fixture", run_dir / "before", today)
                run = Run(case_dir, run_dir, today)
                load_grader(case_dir).grade(run)
            passed = [c["name"] for c in run.checks if c["pass"]]
            print(f"{split:5} {case_dir.name:20} {len(passed)}/{len(run.checks)} checks pass, {len(run.claims)} claims")
            if a.verbose:
                for c in run.checks:
                    print(f"        {'PASS' if c['pass'] else 'fail'} {c['name']}  {c['detail'] if not c['pass'] else ''}"[:160])


def cmd_compare(a):
    old = json.loads((Path(a.old) / "summary.json").read_text())
    new = json.loads((Path(a.new) / "summary.json").read_text())
    print(f"old skill {old['fingerprint']['skill_sha256']}  new skill {new['fingerprint']['skill_sha256']}")
    if (old["model"], old["judge_model"]) != (new["model"], new["judge_model"]):
        print("warning: the two runs used different models, so the scores are not comparable")
    verdict = {}
    for split in ("train", "test"):
        o, n = old["splits"].get(split), new["splits"].get(split)
        if not o or not n or o["mean"] is None or n["mean"] is None:
            continue
        if set(o["cases"]) != set(n["cases"]):
            print(f"warning: {split} case sets differ")
        delta = n["mean"] - o["mean"]
        band = 1.96 * math.sqrt(o["se"] ** 2 + n["se"] ** 2)
        verdict[split] = "up" if delta > band else "down" if delta < -band else "flat"
        print(f"{split}: {o['mean']:.3f} -> {n['mean']:.3f}  delta {delta:+.3f}, noise band +/- {band:.3f}  ({verdict[split]})")
    if verdict.get("train") == "up" and verdict.get("test") == "up":
        print("Keep: train and test both rose beyond noise.")
    elif verdict.get("train") == "up" and verdict.get("test") == "flat":
        print("Unclear: train rose but test is flat. Keep only if the change is general; watch for overfitting.")
    else:
        print("Revert: no gain beyond noise.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("skill")
    r.add_argument("--split", choices=["train", "test", "all"], default="all")
    r.add_argument("--case", help="only cases whose folder name matches this glob")
    r.add_argument("--runs", type=int, default=3)
    r.add_argument("--model", default="sonnet", help="model the skill runs on")
    r.add_argument("--judge-model", default="sonnet")
    r.add_argument("-j", "--concurrency", type=int, default=4)
    r.add_argument("--max-cost", type=float, help="stop launching runs past this many USD")
    r.add_argument("--quiet", action="store_true", help="hide claude plugin eval's own output")
    r.set_defaults(fn=cmd_run)
    d = sub.add_parser("dry")
    d.add_argument("skill")
    d.add_argument("-v", "--verbose", action="store_true")
    d.set_defaults(fn=cmd_dry)
    j = sub.add_parser("rejudge")
    j.add_argument("results")
    j.add_argument("--judge-model")
    j.set_defaults(fn=cmd_rejudge)
    c = sub.add_parser("compare")
    c.add_argument("old")
    c.add_argument("new")
    c.set_defaults(fn=cmd_compare)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
