"""Builds graph.html, the knowledge graph page (spec section 10).

One self-contained file: the graph data and the script are inline and nothing loads from the
network. Standard library only; runs on Python 3.9.

- The data sits in a `<script type="application/json">` block. Every `<`, `>` and `&` in it is
  written as a \\u escape, so no statement can close the block or open a comment, and the `h`
  of any `http` in learner text is escaped too, so the file holds no URL.
- The page puts all text in with `textContent`, never as HTML.
"""
import contextlib
import json
import os
import re
import tempfile

from store import StoreError

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def build(store, goal_id=None):
    """Writes <data>/graph.html and returns its Path.

    `store` is a store.Store. `goal_id` preselects that goal in the page's goal
    picker; None (or an id the page doesn't know) shows every goal.
    """
    store.check_writable()
    path = store.path("graph.html")
    _write_text(path, PAGE.replace("__DATA__", _inline_json(page_data(store, goal_id)), 1))
    return path


def page_data(store, goal_id=None):
    """The JSON the page reads: goals, imported files, propositions and chains.

    Each node's sources become `{"goal", "date", "step", "stepTitle"}` for a taught step (the
    date is the log id's date) or `{"file"}` for imported notes. Goals get a color slot in the
    order they were created, so a goal keeps its color from one build to the next.
    """
    props, chains = store.graph()
    goals = [g for g in store.list_goals() if isinstance(g, dict) and g.get("id")]
    files = {}
    for line in store.read_jsonl("graph/sources.jsonl"):
        if line.get("id"):
            files[line["id"]] = line  # the last line for an id is its latest import

    # Goals named by a node's sources but missing from goals/ still need a title and color.
    known = {g["id"] for g in goals}
    for node in list(props.values()) + list(chains.values()):
        for src in node.get("sources", []):
            gid = src.get("goal") if isinstance(src, dict) else None
            if isinstance(gid, str) and gid and gid not in known:
                known.add(gid)
                goals.append({"id": gid, "title": gid})
    order = sorted(goals, key=lambda g: (not g.get("created"), str(g.get("created") or ""), g["id"]))
    slots = {g["id"]: i % 8 for i, g in enumerate(order)}

    steps = {}
    for g in goals:
        try:
            plan = store.read_plan(g["id"])
        except StoreError:
            plan = None
        steps[g["id"]] = {
            s["id"]: str(s.get("title") or "")
            for s in ((plan or {}).get("steps") or [])
            if isinstance(s, dict) and isinstance(s.get("id"), str)
        }

    def sources(node):
        out = []
        for src in node.get("sources", []):
            if not isinstance(src, dict):
                continue
            if src.get("goal"):
                gid, log, step = str(src["goal"]), str(src.get("log") or ""), src.get("step")
                title = steps.get(gid, {}).get(step) if isinstance(step, str) else None
                out.append({
                    "goal": gid,
                    "date": log[:10] if _DATE.match(log) else None,
                    "step": None if step is None else str(step),
                    "stepTitle": title or None,
                })
            elif src.get("source"):
                out.append({"file": str(src["source"])})
        return out

    def aliases(node):
        seen, out = {str(node.get("statement"))}, []
        for text in node.get("aliases", []):
            if isinstance(text, str) and text not in seen:
                seen.add(text)
                out.append(text)
        return out

    return {
        "selected": goal_id,
        "goals": [
            {"id": g["id"], "title": str(g.get("title") or g["id"]), "status": g.get("status"),
             "color": slots[g["id"]]}
            for g in goals
        ],
        "files": [
            {"id": fid, "name": os.path.basename(str(f.get("path") or "")) or fid,
             "path": str(f.get("path") or ""), "date": str(f.get("at") or "")[:10] or None}
            for fid, f in files.items()
        ],
        "props": [
            {"id": pid, "statement": str(p.get("statement") or ""), "aliases": aliases(p),
             "sources": sources(p)}
            for pid, p in props.items()
        ],
        "chains": [
            {"id": cid, "premises": list(c.get("premises", [])), "conclusion": c.get("conclusion"),
             "sources": sources(c)}
            for cid, c in chains.items()
        ],
    }


def _inline_json(obj):
    """JSON that is safe inside a <script> block and holds no `http`."""
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    text = text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    # JSON has no `\h` escape, so an `h` here is always a plain character inside a string.
    return re.sub(r"[hH](?=[tT][tT][pP])", lambda m: "\\u%04x" % ord(m.group()), text)


def _write_text(path, text):
    """Writes `text` to a temp file next to `path`, then renames it over `path`."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix="." + path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, str(path))
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Study - knowledge graph</title>
<style>
*, *::before, *::after { box-sizing: border-box; }
:root {
  --bg: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink2: #52514e; --muted: #6f6e69;
  --edge: #b9b8b0; --edge-hot: #52514e; --hair: #e1e0d9; --hover: #efeee9; --accent: #2a78d6;
  --file: #a3a29b;
  --g0: #2a78d6; --g1: #eb6834; --g2: #1baf7a; --g3: #eda100;
  --g4: #e87ba4; --g5: #008300; --g6: #6250d6; --g7: #e34948;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink2: #c3c2b7; --muted: #a09f98;
    --edge: #4e4d49; --edge-hot: #c3c2b7; --hair: #2c2c2a; --hover: #262624; --accent: #3987e5;
    --file: #7a7973;
    --g0: #3987e5; --g1: #d95926; --g2: #199e70; --g3: #c98500;
    --g4: #d55181; --g5: #008300; --g6: #9085e9; --g7: #e66767;
  }
}
html, body { margin: 0; height: 100%; }
body {
  display: flex; flex-direction: column; background: var(--bg); color: var(--ink);
  font: 15px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif;
}
button, input, select { font: inherit; color: inherit; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
header {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px;
  padding: 10px 16px; background: var(--surface); border-bottom: 1px solid var(--hair);
}
h1 { flex: 1 1 auto; margin: 0; font-size: 16px; font-weight: 600; }
.controls { display: flex; gap: 8px; flex: 1 1 440px; min-width: 0; max-width: 640px; }
.controls input, .controls select {
  min-width: 0; padding: 7px 10px; background: var(--bg);
  border: 1px solid var(--hair); border-radius: 8px;
}
.controls input { flex: 3 1 0; }
.controls select { flex: 2 1 0; }
main { display: flex; flex: 1 1 auto; min-height: 0; }
.stage { position: relative; flex: 1 1 auto; min-width: 0; background: var(--surface); }
svg { display: block; width: 100%; height: 100%; touch-action: none; user-select: none; cursor: grab; }
svg.grabbing { cursor: grabbing; }
.edge { stroke: var(--edge); stroke-width: 1.3; fill: none; }
.edge.to { marker-end: url(#arrow); }
.edge.hot { stroke: var(--edge-hot); }
.edge.to.hot { marker-end: url(#arrow-hot); }
#arrow path { fill: var(--edge); }
#arrow-hot path { fill: var(--edge-hot); }
.dot { fill: var(--ink2); }
.node { stroke: var(--surface); stroke-width: 1.5; }
.node.sel { stroke: var(--ink); stroke-width: 2.5; }
.dot.sel { fill: var(--ink); }
.faded { opacity: 0.13; }
.off { display: none; }
.label {
  fill: var(--ink); stroke: var(--surface); stroke-linejoin: round;
  paint-order: stroke; pointer-events: none;
}
.tools { position: absolute; right: 10px; bottom: 10px; display: flex; gap: 6px; }
.tools button {
  min-width: 36px; height: 36px; padding: 0 10px; cursor: pointer;
  background: var(--bg); border: 1px solid var(--hair); border-radius: 8px;
}
.notice {
  position: absolute; inset: 0; display: grid; place-items: center;
  padding: 16px; margin: 0; text-align: center; color: var(--ink2); pointer-events: none;
}
.panel {
  flex: 0 0 360px; overflow-y: auto; padding: 14px 16px 24px;
  border-left: 1px solid var(--hair); overflow-wrap: anywhere;
}
.panel p { margin: 0 0 10px; }
.summary { color: var(--ink2); }
.hint { color: var(--ink2); font-size: 13px; }
.legend { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 12px; padding: 0; list-style: none; }
.chip {
  display: inline-flex; align-items: center; gap: 6px; max-width: 100%; padding: 3px 10px;
  font-size: 13px; cursor: pointer; background: var(--surface);
  border: 1px solid var(--hair); border-radius: 999px;
}
.chip:hover, .item:hover { background: var(--hover); }
.chip .t { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.swatch { flex: none; width: 10px; height: 10px; border-radius: 50%; background: var(--c); }
.list { margin: 0; padding: 0; list-style: none; }
.item {
  display: flex; align-items: baseline; gap: 8px; width: 100%; padding: 6px;
  text-align: left; cursor: pointer; background: none; border: 0; border-radius: 6px;
}
.item .swatch { position: relative; top: 1px; }
.back {
  padding: 4px 0; margin: 0 0 8px; cursor: pointer; color: var(--accent);
  background: none; border: 0;
}
.kicker { display: flex; align-items: center; gap: 6px; color: var(--ink2); font-size: 13px; }
.statement { margin: 4px 0 12px; font-size: 18px; line-height: 1.35; }
h3 {
  margin: 18px 0 6px; font-size: 12px; font-weight: 600; letter-spacing: 0.04em;
  text-transform: uppercase; color: var(--ink2);
}
.panel ul.plain { margin: 0; padding-left: 18px; }
.box { margin: 0 0 6px; padding: 4px; border: 1px solid var(--hair); border-radius: 8px; }
.box .note { padding: 2px 6px; font-size: 13px; color: var(--ink2); }
.src { margin: 0 0 10px; }
.src .meta { font-size: 13px; color: var(--ink2); }
.src .path { font-size: 12px; color: var(--muted); }
.empty { max-width: 32em; margin: 18vh auto; padding: 0 16px; text-align: center; color: var(--ink2); }
@media (max-width: 720px) {
  html, body { height: auto; }
  body { display: block; }
  main { display: block; }
  .controls { flex-basis: 100%; max-width: none; }
  .stage { height: 58vh; min-height: 300px; }
  .panel { border-left: 0; border-top: 1px solid var(--hair); }
}
</style>
</head>
<body>
<header>
  <h1>Knowledge graph</h1>
  <div class="controls" id="controls">
    <input type="search" id="search" placeholder="Search ideas" aria-label="Search ideas" autocomplete="off">
    <select id="goal" aria-label="Goal"></select>
  </div>
</header>
<main id="main">
  <section class="stage" id="stage">
    <svg id="graph" role="img" aria-label="Ideas as dots; each small dot is a chain of reasoning, with lines from the ideas it starts from and an arrow to the idea it gives">
      <defs>
        <marker id="arrow" viewBox="0 0 8 8" refX="8" refY="4" markerWidth="8" markerHeight="8" markerUnits="userSpaceOnUse" orient="auto"><path d="M0,0 L8,4 L0,8 z"/></marker>
        <marker id="arrow-hot" viewBox="0 0 8 8" refX="8" refY="4" markerWidth="8" markerHeight="8" markerUnits="userSpaceOnUse" orient="auto"><path d="M0,0 L8,4 L0,8 z"/></marker>
      </defs>
      <g id="view"><g id="edges"></g><g id="dots"></g><g id="nodes"></g><g id="labels"></g></g>
    </svg>
    <p class="notice off" id="notice"></p>
    <div class="tools" id="tools">
      <button type="button" id="zoom-in" aria-label="Zoom in">+</button>
      <button type="button" id="zoom-out" aria-label="Zoom out">-</button>
      <button type="button" id="fit">Fit</button>
    </div>
  </section>
  <aside class="panel" id="panel" aria-live="polite"></aside>
</main>
<p class="empty off" id="empty">Your knowledge graph is empty. It fills in as you study a goal with /study, and when you add your own notes with /import-notes.</p>
<script type="application/json" id="graph-data">__DATA__</script>
<script>
"use strict";
(function () {
  const D = JSON.parse(document.getElementById("graph-data").textContent);
  const $ = (id) => document.getElementById(id);
  const svg = $("graph"), view = $("view"), NS = svg.namespaceURI;
  const gEdges = $("edges"), gDots = $("dots"), gNodes = $("nodes"), gLabels = $("labels");
  const panel = $("panel"), search = $("search"), picker = $("goal"), notice = $("notice");
  const FILES = "@files";

  if (!D.props.length) {
    $("controls").classList.add("off");
    $("main").classList.add("off");
    $("empty").classList.remove("off");
    return;
  }

  const goalById = new Map(D.goals.map((g) => [g.id, g]));
  const fileById = new Map(D.files.map((f) => [f.id, f]));

  function svgEl(tag, cls, parent) {
    const el = document.createElementNS(NS, tag);
    el.setAttribute("class", cls);
    parent.appendChild(el);
    return el;
  }

  // h("p", {class: "x", onclick: fn}, "text", child) - text always goes in as text.
  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === "class") el.className = v;
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v);
    }
    for (const kid of kids.flat(Infinity)) if (kid != null && kid !== false) el.append(kid);
    return el;
  }

  function origins(sources) {
    const goals = [], files = [];
    for (const s of sources) {
      if (s.goal && !goals.includes(s.goal)) goals.push(s.goal);
      if (s.file && !files.includes(s.file)) files.push(s.file);
    }
    return { goals, files };
  }

  // Bodies of the layout: propositions, and one small dot per chain.
  const props = D.props.map((p) => Object.assign(origins(p.sources), {
    kind: "prop", id: p.id, statement: p.statement, aliases: p.aliases, sources: p.sources,
    text: (p.statement + "\n" + p.aliases.join("\n")).toLowerCase(),
    chainsIn: [], chainsOut: [], r: 6, charge: -150,
    x: 0, y: 0, vx: 0, vy: 0, fx: null, fy: null,
  }));
  const propById = new Map(props.map((p) => [p.id, p]));
  const chains = [];
  for (const c of D.chains) {
    const premises = c.premises.map((id) => propById.get(id)).filter(Boolean);
    const conclusion = propById.get(c.conclusion);
    if (!premises.length || !conclusion) continue;
    const chain = Object.assign(origins(c.sources), {
      kind: "chain", id: c.id, premises, conclusion, sources: c.sources, r: 3, charge: -30,
      x: 0, y: 0, vx: 0, vy: 0, fx: null, fy: null,
    });
    chains.push(chain);
    conclusion.chainsIn.push(chain);
    for (const p of premises) if (!p.chainsOut.includes(chain)) p.chainsOut.push(chain);
  }

  // Start on a sunflower spiral in the order taught, so nearby ideas start near each other.
  props.forEach((p, i) => {
    const rad = 14 * Math.sqrt(i + 0.5), a = i * Math.PI * (3 - Math.sqrt(5));
    p.x = rad * Math.cos(a);
    p.y = rad * Math.sin(a);
    p.r = 6 + Math.min(4, 1.4 * Math.sqrt(p.chainsIn.length + p.chainsOut.length));
  });
  chains.forEach((c, i) => {
    const ends = c.premises.concat([c.conclusion]);
    c.x = ends.reduce((s, p) => s + p.x, 0) / ends.length + ((i % 7) - 3) * 0.7;
    c.y = ends.reduce((s, p) => s + p.y, 0) / ends.length + ((i % 5) - 2) * 0.7;
  });

  // SVG elements
  for (const c of chains) {
    c.lines = c.premises.map(() => svgEl("line", "edge", gEdges));
    c.arrow = svgEl("line", "edge to", gEdges);
    c.el = svgEl("circle", "dot", gDots);
    c.el.setAttribute("r", c.r);
  }
  const measure = document.createElement("canvas").getContext("2d");
  measure.font = "12px " + getComputedStyle(document.body).fontFamily;
  for (const p of props) {
    p.el = svgEl("circle", "node", gNodes);
    p.el.setAttribute("r", p.r);
    p.label = svgEl("text", "label off", gLabels);
    p.label.textContent = p.statement.length > 32 ? p.statement.slice(0, 30).trimEnd() + "…" : p.statement;
    p.labelW = measure.measureText(p.label.textContent).width + 6;
  }

  const state = { filter: "", words: [], sel: null };
  let shownProps = [], shownChains = [], bodies = [], links = [];

  function goalTitle(id) { return goalById.has(id) ? goalById.get(id).title : id; }
  function colorOf(p) {
    const id = state.filter && p.goals.includes(state.filter) ? state.filter : p.goals[0];
    return id && goalById.has(id) ? "var(--g" + goalById.get(id).color + ")" : "var(--file)";
  }
  function homeOf(p) {
    return p.goals.length ? { title: goalTitle(p.goals[0]), color: colorOf(p) } : { title: "Imported notes", color: "var(--file)" };
  }

  // Goal picker: all goals, each goal (newest first), imported notes.
  picker.append(h("option", { value: "" }, "All goals"));
  for (const g of D.goals) picker.append(h("option", { value: g.id }, g.title + (g.status === "done" ? " (done)" : "")));
  if (props.some((p) => p.files.length)) picker.append(h("option", { value: FILES }, "Imported notes"));

  function inFilter(x) {
    if (!state.filter) return true;
    return state.filter === FILES ? x.files.length > 0 : x.goals.includes(state.filter);
  }

  // One goal shows its own ideas, the chains taught in it, and the ends of those chains, so an
  // idea from another goal that a chain here builds on still shows.
  function applyFilter() {
    shownChains = chains.filter((c) => inFilter(c) || (c.premises.every(inFilter) && inFilter(c.conclusion)));
    const keep = new Set(props.filter(inFilter));
    for (const c of shownChains) { c.premises.forEach((p) => keep.add(p)); keep.add(c.conclusion); }
    shownProps = props.filter((p) => keep.has(p));
    const chainSet = new Set(shownChains);
    for (const p of props) {
      const on = keep.has(p);
      p.el.classList.toggle("off", !on);
      if (!on) p.label.classList.add("off");
      p.el.style.fill = colorOf(p);
    }
    for (const c of chains) {
      const on = chainSet.has(c);
      c.el.classList.toggle("off", !on);
      c.arrow.classList.toggle("off", !on);
      c.lines.forEach((l) => l.classList.toggle("off", !on));
    }
    bodies = shownProps.concat(shownChains);
    links = [];
    for (const c of shownChains) {
      for (const p of c.premises) links.push({ a: p, b: c, len: 42 });
      links.push({ a: c, b: c.conclusion, len: 48 });
    }
    if (state.sel && !(state.sel.kind === "prop" ? keep.has(state.sel) : chainSet.has(state.sel))) state.sel = null;
    notice.textContent = shownProps.length ? "" : "Nothing from this goal is in the graph yet.";
    notice.classList.toggle("off", shownProps.length > 0);
  }

  // Force layout: springs on chain lines, repulsion between all bodies, a pull to the middle.
  const ALPHA_MIN = 0.002, DECAY = 1 - Math.pow(ALPHA_MIN, 1 / 300), FRICTION = 0.6;
  let alpha = 1, alphaTarget = 0, running = false;

  function tick() {
    alpha += (alphaTarget - alpha) * DECAY;
    for (const l of links) {
      const a = l.a, b = l.b;
      let dx = b.x + b.vx - a.x - a.vx, dy = b.y + b.vy - a.y - a.vy;
      const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
      const f = ((d - l.len) / d) * alpha * 0.5;
      dx *= f; dy *= f;
      b.vx -= dx / 2; b.vy -= dy / 2;
      a.vx += dx / 2; a.vy += dy / 2;
    }
    const n = bodies.length;
    for (let i = 0; i < n; i++) {
      const a = bodies[i];
      for (let j = i + 1; j < n; j++) {
        const b = bodies[j];
        let dx = b.x - a.x, dy = b.y - a.y, d2 = dx * dx + dy * dy;
        if (d2 > 250000) continue;
        if (d2 < 0.01) { dx = 0.1 * ((i % 3) - 1 || 1); dy = 0.1; d2 = dx * dx + dy * dy; }
        const f = alpha / Math.max(d2, 1);
        a.vx += dx * b.charge * f; a.vy += dy * b.charge * f;
        b.vx -= dx * a.charge * f; b.vy -= dy * a.charge * f;
        const min = a.r + b.r + 4;
        if (d2 < min * min) {
          const d = Math.sqrt(d2), push = ((min - d) / d) * 0.35;
          a.vx -= dx * push; a.vy -= dy * push;
          b.vx += dx * push; b.vy += dy * push;
        }
      }
    }
    const box = stageSize();
    const gx = 0.06 * Math.sqrt(box.h / box.w), gy = 0.06 * Math.sqrt(box.w / box.h);
    for (const b of bodies) {
      b.vx -= b.x * gx * alpha; b.vy -= b.y * gy * alpha;
      if (b.fx != null) { b.x = b.fx; b.y = b.fy; b.vx = b.vy = 0; continue; }
      b.vx *= FRICTION; b.vy *= FRICTION;
      b.x += b.vx; b.y += b.vy;
    }
  }

  function draw() {
    for (const p of shownProps) { p.el.setAttribute("cx", p.x); p.el.setAttribute("cy", p.y); }
    for (const c of shownChains) {
      c.el.setAttribute("cx", c.x); c.el.setAttribute("cy", c.y);
      c.premises.forEach((p, i) => {
        const l = c.lines[i];
        l.setAttribute("x1", p.x); l.setAttribute("y1", p.y);
        l.setAttribute("x2", c.x); l.setAttribute("y2", c.y);
      });
      const t = c.conclusion, dx = t.x - c.x, dy = t.y - c.y, d = Math.sqrt(dx * dx + dy * dy) || 1;
      const end = Math.max(0, d - t.r - 2) / d;
      c.arrow.setAttribute("x1", c.x); c.arrow.setAttribute("y1", c.y);
      c.arrow.setAttribute("x2", c.x + dx * end); c.arrow.setAttribute("y2", c.y + dy * end);
    }
  }

  const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  function settle(ms) {
    const t0 = performance.now();
    while (alpha > ALPHA_MIN && performance.now() - t0 < ms) tick();
  }
  function frame() {
    const t0 = performance.now();
    do tick(); while (alpha > ALPHA_MIN && performance.now() - t0 < 8);
    draw();
    if (autoFit) fit(); else placeLabels();
    if (alpha > ALPHA_MIN || alphaTarget > 0) requestAnimationFrame(frame);
    else running = false;
  }
  function heat(a) {
    alpha = Math.max(alpha, a);
    if (still && alphaTarget === 0) { settle(600); alpha = 0; draw(); if (autoFit) fit(); else placeLabels(); return; }
    if (!running) { running = true; requestAnimationFrame(frame); }
  }

  // Pan and zoom: the view group is translated by (tx, ty) and scaled by k.
  let tx = 0, ty = 0, k = 1, autoFit = true;
  function stageSize() {
    const r = svg.getBoundingClientRect();
    return { w: r.width || 1, h: r.height || 1, left: r.left, top: r.top };
  }
  function setView(x, y, s) {
    tx = x; ty = y; k = s;
    view.setAttribute("transform", "translate(" + tx + "," + ty + ") scale(" + k + ")");
    gLabels.style.fontSize = 12 / k + "px";
    gLabels.style.strokeWidth = 3 / k + "px";
    placeLabels();
  }
  function zoomAt(x, y, s) {
    s = Math.min(4, Math.max(0.08, s));
    setView(x - ((x - tx) / k) * s, y - ((y - ty) / k) * s, s);
    autoFit = false;
  }
  function fit() {
    if (!shownProps.length) return;
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const b of bodies) {
      x0 = Math.min(x0, b.x - b.r); y0 = Math.min(y0, b.y - b.r);
      x1 = Math.max(x1, b.x + b.r); y1 = Math.max(y1, b.y + b.r);
    }
    const box = stageSize(), pad = 28;
    const s = Math.min(1.4, Math.max(0.08, Math.min((box.w - 2 * pad) / (x1 - x0 || 1), (box.h - 2 * pad - 40) / (y1 - y0 || 1))));
    setView(box.w / 2 - s * (x0 + x1) / 2, (box.h - 40) / 2 - s * (y0 + y1) / 2, s);
  }
  function centerOn(item) {
    const box = stageSize(), s = Math.max(k, 1.2);
    setView(box.w / 2 - item.x * s, (box.h - 40) / 2 - item.y * s, s);
    autoFit = false;
  }

  // Pointer input: drag a node, drag the background to pan, pinch to zoom, tap to select.
  const pointers = new Map();
  let gesture = null;
  function local(e) { const box = stageSize(); return { x: e.clientX - box.left, y: e.clientY - box.top }; }
  function hitTest(pt) {
    const gx = (pt.x - tx) / k, gy = (pt.y - ty) / k;
    let best = null, bestD = Infinity;
    for (const list of [shownProps, shownChains]) {
      for (const b of list) {
        const d = Math.hypot(b.x - gx, b.y - gy);
        if (d < b.r + 9 / k && d < bestD) { best = b; bestD = d; }
      }
      if (best) return best;
    }
    return null;
  }
  svg.addEventListener("pointerdown", (e) => {
    svg.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, local(e));
    if (pointers.size === 2) {
      if (gesture && gesture.hit) { gesture.hit.fx = gesture.hit.fy = null; alphaTarget = 0; }
      const [a, b] = [...pointers.values()];
      gesture = { pinch: true, d: Math.hypot(a.x - b.x, a.y - b.y) || 1, mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2, tx, ty, k };
      return;
    }
    if (pointers.size > 2) return;
    const pt = local(e), hit = hitTest(pt);
    gesture = { hit, x: pt.x, y: pt.y, tx, ty, moved: false };
    svg.classList.add("grabbing");
  });
  svg.addEventListener("pointermove", (e) => {
    if (!pointers.has(e.pointerId) || !gesture) return;
    const pt = local(e);
    pointers.set(e.pointerId, pt);
    if (gesture.pinch) {
      if (pointers.size < 2) return;
      const [a, b] = [...pointers.values()];
      const s = Math.min(4, Math.max(0.08, gesture.k * (Math.hypot(a.x - b.x, a.y - b.y) / gesture.d)));
      const gx = (gesture.mx - gesture.tx) / gesture.k, gy = (gesture.my - gesture.ty) / gesture.k;
      setView((a.x + b.x) / 2 - gx * s, (a.y + b.y) / 2 - gy * s, s);
      autoFit = false;
      return;
    }
    if (!gesture.moved && Math.hypot(pt.x - gesture.x, pt.y - gesture.y) < 4) return;
    gesture.moved = true;
    autoFit = false;
    if (gesture.hit) {
      gesture.hit.fx = (pt.x - tx) / k;
      gesture.hit.fy = (pt.y - ty) / k;
      alphaTarget = 0.3;
      heat(0.3);
    } else {
      setView(gesture.tx + pt.x - gesture.x, gesture.ty + pt.y - gesture.y, k);
    }
  });
  function pointerEnd(e) {
    if (!pointers.delete(e.pointerId)) return;
    if (gesture && !gesture.pinch) {
      if (gesture.hit) { gesture.hit.fx = gesture.hit.fy = null; alphaTarget = 0; }
      if (!gesture.moved && e.type === "pointerup") select(gesture.hit, false);
    }
    if (!pointers.size || (gesture && gesture.pinch)) gesture = null;
    svg.classList.remove("grabbing");
  }
  svg.addEventListener("pointerup", pointerEnd);
  svg.addEventListener("pointercancel", pointerEnd);
  svg.addEventListener("wheel", (e) => {
    e.preventDefault();
    const pt = local(e);
    zoomAt(pt.x, pt.y, k * Math.exp(-e.deltaY * (e.deltaMode ? 0.05 : 0.0025)));
  }, { passive: false });
  $("zoom-in").addEventListener("click", () => { const b = stageSize(); zoomAt(b.w / 2, b.h / 2, k * 1.4); });
  $("zoom-out").addEventListener("click", () => { const b = stageSize(); zoomAt(b.w / 2, b.h / 2, k / 1.4); });
  $("fit").addEventListener("click", () => { autoFit = true; fit(); });
  window.addEventListener("resize", () => { if (autoFit) fit(); });

  // Highlight: the selection and its neighbors, else the search matches.
  function matches(p) { return state.words.every((w) => p.text.includes(w)); }
  function focus() {
    const sel = state.sel;
    if (sel) {
      const nodes = new Set(), hot = new Set();
      const list = sel.kind === "prop" ? sel.chainsIn.concat(sel.chainsOut) : [sel];
      if (sel.kind === "prop") nodes.add(sel);
      for (const c of list) {
        if (!shownChains.includes(c)) continue;
        hot.add(c);
        c.premises.forEach((p) => nodes.add(p));
        nodes.add(c.conclusion);
      }
      return { nodes, hot, fromSelection: true };
    }
    if (state.words.length) {
      const nodes = new Set(shownProps.filter(matches));
      const hot = new Set(shownChains.filter((c) => nodes.has(c.conclusion) && c.premises.every((p) => nodes.has(p))));
      return { nodes, hot, fromSelection: false };
    }
    return null;
  }
  let lastFocus = null;
  function applyFocus() {
    const f = lastFocus = focus();
    for (const p of shownProps) {
      p.el.classList.toggle("faded", !!f && !f.nodes.has(p));
      p.el.classList.toggle("sel", state.sel === p);
    }
    for (const c of shownChains) {
      const faded = !!f && !f.hot.has(c), hot = !!f && f.hot.has(c);
      c.el.classList.toggle("faded", faded && state.sel !== c);
      c.el.classList.toggle("sel", state.sel === c);
      for (const l of c.lines.concat([c.arrow])) { l.classList.toggle("faded", faded); l.classList.toggle("hot", hot); }
    }
    placeLabels();
  }

  // Labels go where they overlap no other label, node or the zoom buttons: right of the node,
  // else left. The selection comes first (and may cover a node), then the ideas with the most chains.
  function placeLabels() {
    const f = lastFocus, box = stageSize(), tools = $("tools").getBoundingClientRect();
    const taken = [{ x0: tools.left - box.left - 4, y0: tools.top - box.top - 4, x1: box.w, y1: box.h }];
    const near = shownProps.filter((p) => !f || f.nodes.has(p));
    const dots = near.map((p) => ({ x: k * p.x + tx, y: k * p.y + ty, r: k * p.r + 2 }));
    const rank = (p) => (p === state.sel ? 1e6 : 0) + p.chainsIn.length + p.chainsOut.length;
    const order = near.slice().sort((a, b) => rank(b) - rank(a));
    for (const p of shownProps) p.label.classList.add("off");
    for (const p of order) {
      const sx = k * p.x + tx, sy = k * p.y + ty, gap = k * p.r + 4;
      for (const side of [1, -1]) {
        const x0 = side > 0 ? sx + gap : sx - gap - p.labelW;
        const b = { x0, y0: sy - 8, x1: x0 + p.labelW, y1: sy + 8 };
        if (b.x0 < 2 || b.x1 > box.w - 2 || b.y0 < 2 || b.y1 > box.h - 2) continue;
        if (taken.some((o) => o.x0 < b.x1 && b.x0 < o.x1 && o.y0 < b.y1 && b.y0 < o.y1)) continue;
        if (p !== state.sel && dots.some((d) => Math.hypot(Math.max(b.x0, Math.min(d.x, b.x1)) - d.x, Math.max(b.y0, Math.min(d.y, b.y1)) - d.y) < d.r)) continue;
        taken.push(b);
        p.label.setAttribute("x", p.x + side * (p.r + 4 / k));
        p.label.setAttribute("y", p.y + 4 / k);
        p.label.setAttribute("text-anchor", side > 0 ? "start" : "end");
        p.label.classList.remove("off");
        break;
      }
    }
  }

  function select(item, center) {
    state.sel = item || null;
    applyFocus();
    renderPanel();
    if (item && center) centerOn(item);
  }
  function selectProp(p) {
    if (!shownProps.includes(p)) { state.filter = picker.value = ""; refilter(); }
    select(p, true);
    panel.scrollTop = 0;
  }

  // Side panel: the list of ideas, or one idea or chain.
  function swatch(color) { const s = h("span", { class: "swatch" }); s.style.setProperty("--c", color); return s; }
  function propButton(p) {
    return h("button", { type: "button", class: "item", onclick: () => selectProp(p) }, swatch(colorOf(p)), h("span", null, p.statement));
  }
  function sourceItem(s) {
    if (s.file) {
      const f = fileById.get(s.file) || { name: s.file, path: "", date: null };
      return h("div", { class: "src" }, h("div", null, f.name),
        h("div", { class: "meta" }, f.date ? "Imported notes, " + f.date : "Imported notes"),
        f.path ? h("div", { class: "path" }, f.path) : null);
    }
    const step = s.step ? "step " + s.step + (s.stepTitle ? ": " + s.stepTitle : "") : null;
    return h("div", { class: "src" }, h("div", null, goalTitle(s.goal)),
      h("div", { class: "meta" }, [s.date, step].filter(Boolean).join(", ") || "date not recorded"));
  }
  function taught(sources) {
    return sources.length ? [h("h3", null, "Where it was taught")].concat(sources.map(sourceItem)) : [];
  }
  function backButton() { return h("button", { type: "button", class: "back", onclick: () => select(null) }, "← All ideas"); }

  function renderPanel() {
    panel.replaceChildren();
    const sel = state.sel;
    if (sel && sel.kind === "prop") {
      const home = homeOf(sel);
      panel.append(backButton(), h("p", { class: "kicker" }, swatch(home.color), home.title), h("h2", { class: "statement" }, sel.statement));
      if (sel.aliases.length) panel.append(h("h3", null, "Also said as"), h("ul", { class: "plain" }, sel.aliases.map((a) => h("li", null, a))));
      if (sel.chainsIn.length) {
        panel.append(h("h3", null, "Follows from"));
        for (const c of sel.chainsIn) panel.append(h("div", { class: "box" }, c.premises.map(propButton)));
      }
      if (sel.chainsOut.length) {
        panel.append(h("h3", null, "Leads to"));
        for (const c of sel.chainsOut) {
          const others = c.premises.filter((p) => p !== sel);
          panel.append(h("div", { class: "box" },
            others.length ? [h("div", { class: "note" }, "Together with"), others.map(propButton), h("div", { class: "note" }, "it gives")] : null,
            propButton(c.conclusion)));
        }
      }
      panel.append(...taught(sel.sources));
      return;
    }
    if (sel && sel.kind === "chain") {
      panel.append(backButton(), h("p", { class: "kicker" }, "A chain of reasoning"),
        h("h3", null, "From"), h("div", { class: "box" }, sel.premises.map(propButton)),
        h("h3", null, "Gives"), h("div", { class: "box" }, propButton(sel.conclusion)));
      panel.append(...taught(sel.sources));
      return;
    }
    const list = state.words.length ? shownProps.filter(matches) : shownProps;
    const ideas = (n) => n + (n === 1 ? " idea" : " ideas");
    const summary = state.words.length
      ? (list.length ? list.length + " of " + ideas(shownProps.length) + " match." : "No ideas match “" + search.value.trim() + "”.")
      : ideas(shownProps.length) + " and " + shownChains.length + (shownChains.length === 1 ? " chain." : " chains.");
    panel.append(h("p", { class: "summary" }, summary));
    if (!state.filter) {
      const chips = D.goals.filter((g) => props.some((p) => p.goals[0] === g.id)).map((g) =>
        h("li", null, h("button", { type: "button", class: "chip", onclick: () => pick(g.id) }, swatch("var(--g" + g.color + ")"), h("span", { class: "t" }, g.title))));
      if (props.some((p) => !p.goals.length)) {
        chips.push(h("li", null, h("button", { type: "button", class: "chip", onclick: () => pick(FILES) }, swatch("var(--file)"), h("span", { class: "t" }, "Imported notes"))));
      }
      if (chips.length > 1) panel.append(h("ul", { class: "legend", "aria-label": "Colors by goal" }, chips));
    }
    if (!state.words.length) panel.append(h("p", { class: "hint" }, "Select an idea to see what it follows from, what it leads to and where it was taught. Each small dot is a chain of reasoning: lines come in from the ideas it starts from, and an arrow points to the idea it gives."));
    panel.append(h("ul", { class: "list" }, list.map((p) => h("li", null, propButton(p)))));
  }

  function refilter() {
    applyFilter();
    autoFit = true;
    applyFocus();
    renderPanel();
    heat(0.5);
    if (!running) fit();
  }
  function pick(value) { state.filter = picker.value = value; state.sel = null; refilter(); }

  picker.addEventListener("change", () => pick(picker.value));
  search.addEventListener("input", () => {
    state.words = search.value.toLowerCase().split(/\s+/).filter(Boolean);
    state.sel = null;
    applyFocus();
    renderPanel();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement !== search) { e.preventDefault(); search.focus(); }
    else if (e.key === "Escape") {
      if (state.sel) select(null);
      else if (search.value) { search.value = ""; search.dispatchEvent(new Event("input")); }
    }
  });

  state.filter = picker.value = [...picker.options].some((o) => o.value === D.selected) ? D.selected : "";
  applyFilter();
  settle(still ? 1500 : 250);
  if (still) alpha = 0;
  draw();
  fit();
  applyFocus();
  renderPanel();
  heat(0);
})();
</script>
</body>
</html>
"""
