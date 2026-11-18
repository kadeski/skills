#!/usr/bin/env python3
"""Find which lines of a skill the model already follows without it.

    evals/novelty.py <skill> [--atom ID ...] [--samples 3] [--model sonnet] [--judge-model opus]

`evals/<skill>/atoms.yaml` splits SKILL.md into atoms: one rule each, as a
situation question that doesn't give the answer away and the exact answer the
skill expects. Each question goes to the model with and without SKILL.md in
its system prompt, `--samples` times each, and a judge grades every answer
strictly: the full rule, conditions included, or it fails. An arm passes an
atom when most samples pass. That sorts each atom into:

    known    right without the skill    cut candidate
    added    right only with it         keep
    hurts    right only without it      fix first
    missed   wrong both ways            rewrite or accept

A cut is only proposed: confirm it with the skill's task evals (evals/run.py,
tests/<plugin>/) before keeping it. See evals/README.md, "Prune a skill".
"""

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"

ANSWER_SYSTEM = "You are a coding agent. Answer the question about what you would do, in at most 6 sentences. Be concrete: commit to one course of action."
SKILL_PREFIX = "\n\nYou have this skill loaded for the task. Follow it.\n\n<skill>\n{skill}\n</skill>"

JUDGE_SYSTEM = """You grade a coding agent's answers against the expected answer. \
Grade strictly: an answer passes only if it commits to every part of the \
expected answer, including its exact conditions, values, names and order, and \
any "and stop", "and wait" or "don't" part. Knowing the general idea is not \
enough. Extra detail is fine unless it contradicts the expected answer. An \
answer that hedges between options, or only mentions the expected action as \
one possibility, fails."""

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"n": {"type": "integer"}, "pass": {"type": "boolean"}, "reason": {"type": "string"}},
                "required": ["n", "pass", "reason"],
            },
        }
    },
    "required": ["verdicts"],
}


def claude(system, prompt, model, schema=None):
    cmd = ["claude", "-p", "--model", model, "--tools", "", "--no-session-persistence",
           "--strict-mcp-config", "--setting-sources", "", "--disable-slash-commands",
           "--settings", '{"autoMemoryEnabled":false}',
           "--system-prompt", system, "--output-format", "json"]
    if schema:
        cmd += ["--json-schema", json.dumps(schema)]
    with tempfile.TemporaryDirectory() as cwd:
        out = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=cwd, timeout=600,
                             env={**os.environ, "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"})
    res = json.loads(out.stdout)
    return res, res.get("total_cost_usd", 0)


def skill_path(skill):
    hits = list((ROOT / "plugins").glob(f"*/skills/{skill}/SKILL.md"))
    if len(hits) != 1:
        sys.exit(f"no single SKILL.md for {skill}: {hits}")
    return hits[0]


def probe(atom, stem, skill_text, a):
    q = f"{stem}\n\n{atom['q']}".strip()
    jobs = [(arm, i) for arm in ("without", "with") for i in range(a.samples)]

    def ask(job):
        arm, _ = job
        system = ANSWER_SYSTEM + (SKILL_PREFIX.format(skill=skill_text) if arm == "with" else "")
        res, cost = claude(system, q, a.model)
        return arm, res.get("result", ""), cost

    with ThreadPoolExecutor(len(jobs)) as ex:
        answers = list(ex.map(ask, jobs))
    listing = "\n\n".join(f"## Answer {n}\n{ans}" for n, (_, ans, _) in enumerate(answers))
    prompt = f"# Question\n{q}\n\n# Expected answer\n{atom['a']}\n\n{listing}\n\nRule on every answer by its number."
    res, jcost = claude(JUDGE_SYSTEM, prompt, a.judge_model, JUDGE_SCHEMA)
    got = {v["n"]: v for v in (res.get("structured_output") or {}).get("verdicts", [])}
    arms = {"without": [], "with": []}
    for n, (arm, ans, _) in enumerate(answers):
        v = got.get(n, {"pass": False, "reason": "judge gave no verdict"})
        arms[arm].append({"pass": bool(v["pass"]), "reason": v["reason"], "answer": ans})
    ok = {arm: sum(r["pass"] for r in rs) * 2 > len(rs) for arm, rs in arms.items()}
    verdict = {(True, True): "known", (False, True): "added", (True, False): "hurts", (False, False): "missed"}[
        (ok["without"], ok["with"])]
    cost = sum(c for _, _, c in answers) + jcost
    return {"id": atom["id"], "kind": atom.get("kind", "idea"), "verdict": verdict,
            "without": sum(r["pass"] for r in arms["without"]), "with": sum(r["pass"] for r in arms["with"]),
            "samples": a.samples, "lines": atom.get("lines", ""), "arms": arms, "cost": cost}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("skill")
    p.add_argument("--atom", nargs="*", help="only these atom ids")
    p.add_argument("--samples", type=int, default=3)
    p.add_argument("--model", default="sonnet")
    p.add_argument("--judge-model", default="opus")
    p.add_argument("--jobs", type=int, default=4, help="atoms probed at once")
    a = p.parse_args()

    spec = yaml.safe_load((EVALS / a.skill / "atoms.yaml").read_text())
    atoms = [x for x in spec["atoms"] if not a.atom or x["id"] in a.atom]
    skill_text = skill_path(a.skill).read_text()
    with ThreadPoolExecutor(a.jobs) as ex:
        rows = list(ex.map(lambda x: probe(x, spec.get("stem", ""), skill_text, a), atoms))

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = EVALS / "results" / f"novelty-{a.skill}-{stamp}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"skill": a.skill, "model": a.model, "judge_model": a.judge_model,
                               "skill_bytes": len(skill_text.encode()), "rows": rows}, indent=1))
    order = {"hurts": 0, "missed": 1, "known": 2, "added": 3}
    for r in sorted(rows, key=lambda r: (order[r["verdict"]], r["id"])):
        print(f"{r['verdict']:7} {r['id']:24} {r['kind']:8} without {r['without']}/{r['samples']}  with {r['with']}/{r['samples']}  {r['lines'][:60]}")
    counts = {v: sum(r["verdict"] == v for r in rows) for v in order}
    print(f"\n{len(rows)} atoms: " + ", ".join(f"{k} {v}" for k, v in counts.items())
          + f"  cost ${sum(r['cost'] for r in rows):.2f}\n{out}")


if __name__ == "__main__":
    main()
