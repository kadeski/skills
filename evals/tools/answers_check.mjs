#!/usr/bin/env node
// tutor's site/answers.js must do nothing, and throw nothing, where it has no
// database: with no `claude` global (file://, other hosts), with a `claude`
// whose capabilities resolve null (signed out, not granted), and with no user id.
// Any touch of `document` counts as doing something.
//
//     node evals/tools/answers_check.mjs

import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const repo = join(dirname(fileURLToPath(import.meta.url)), "../..");
const code = readFileSync(join(repo, "plugins/tutor/skills/tutor/site/answers.js"), "utf8");

const cases = {
  "no claude global": {},
  "claude.use resolves null": { claude: { use: async () => null } },
  "no user id": { claude: { use: async name => (name == "user" ? { id: async () => null } : {}) } },
};

let failed = 0;
for (const [name, globals] of Object.entries(cases)) {
  const touched = [];
  const document = new Proxy({}, { get: (_, k) => { touched.push(String(k)); throw new Error("document." + String(k)); } });
  const window = { ...globals };
  const ctx = vm.createContext({ ...globals, window, document, location: { pathname: "/02-x.html" } });
  let error = null;
  try {
    await vm.runInContext(code, ctx);
  } catch (e) {
    error = e;
  }
  const bad = error ? `threw ${error.message}` : touched.length ? `touched document.${touched[0]}` : "";
  if (bad) failed++;
  console.log(`${bad ? "FAIL" : "PASS"} ${name}${bad ? ": " + bad : ""}`);
}
process.exit(failed ? 1 : 0);
