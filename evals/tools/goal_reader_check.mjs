#!/usr/bin/env node
// Run the goal.md reader from tutor's site/index.html over every fixture goal.md
// and check its plan items and rules against the lines in each section.
//
//     node evals/tools/goal_reader_check.mjs

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const repo = join(dirname(fileURLToPath(import.meta.url)), "../..");
const html = readFileSync(join(repo, "plugins/tutor/skills/tutor/site/index.html"), "utf8");
const ctx = vm.createContext({});
vm.runInContext(html.match(/<script id="reader">([\s\S]*?)<\/script>/)[1], ctx);

function* goals(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) yield* goals(p);
    else if (name == "goal.md") yield p;
  }
}

function lines(text, section) {
  const out = [];
  let cur = "";
  for (const l of text.split("\n")) {
    if (l.startsWith("## ")) cur = l.slice(3).trim().toLowerCase();
    else if (cur == section && l.startsWith("- ")) out.push(l.slice(2).trim());
  }
  return out;
}

let failed = 0, checked = 0;
for (const path of goals(join(repo, "evals/tutor"))) {
  const text = readFileSync(path, "utf8");
  const g = ctx.readGoal(text);
  const bad = [];
  if (!g.title) bad.push("no title");
  const plan = lines(text, "plan");
  if (g.plan.length != plan.length) bad.push(`plan: ${g.plan.length} items, ${plan.length} lines`);
  plan.forEach((l, k) => {
    const i = g.plan[k] || {};
    const linked = l.startsWith("[");
    const status = linked ? (l.split(") - ")[1] || "") : (l.includes(" - ") ? l.slice(l.lastIndexOf(" - ") + 3) : "");
    if (!!i.href != linked) bad.push(`plan ${k + 1}: href ${JSON.stringify(i.href)} for ${l}`);
    if (linked && !l.includes(`](${i.href})`)) bad.push(`plan ${k + 1}: href ${i.href} not in ${l}`);
    if (!l.includes(i.title)) bad.push(`plan ${k + 1}: title ${JSON.stringify(i.title)} not in ${l}`);
    if (i.status != status.trim()) bad.push(`plan ${k + 1}: status ${JSON.stringify(i.status)}, want ${JSON.stringify(status)}`);
  });
  const rules = lines(text, "rules");
  if (g.rules.length != rules.length) bad.push(`rules: ${g.rules.length} read, ${rules.length} lines`);
  g.rules.forEach((r, k) => {
    if (r.learned != rules[k]?.includes("learned")) bad.push(`rule ${r.id}: learned ${r.learned}`);
    if (!r.learned && !rules[k]?.includes(`next ${r.next}`)) bad.push(`rule ${r.id}: next ${r.next}`);
  });
  checked++;
  if (bad.length) {
    failed++;
    console.log(`FAIL ${path.slice(repo.length + 1)}`);
    for (const b of bad) console.log(`     ${b}`);
  }
}
console.log(`${checked - failed} of ${checked} goal.md files read right`);
process.exit(failed ? 1 : 0);
