#!/usr/bin/env node
// Speaks JSON-RPC to the tutor plugin's MCP server and checks its answers.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import { createInterface } from "node:readline";
import { fileURLToPath } from "node:url";

const repo = (p) => fileURLToPath(new URL(`../../${p}`, import.meta.url));
const server = repo("plugins/tutor/server/lesson.mjs");
const lessonDir = repo("evals/tutor/test/chat-answers-done/fixture/cwd/percent-change");
const lesson = `${lessonDir}/02-percent-of-a-number.html`;
const svg = `${lessonDir}/img/02-per-hundred.svg`;

const child = spawn(process.execPath, [server], { stdio: ["pipe", "pipe", "pipe"] });
const lines = createInterface({ input: child.stdout })[Symbol.asyncIterator]();
const errLines = createInterface({ input: child.stderr })[Symbol.asyncIterator]();
let nextId = 1;

async function call(method, params) {
  const id = nextId++;
  child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n");
  const { value, done } = await lines.next();
  assert.ok(!done, `server answered ${method}`);
  const msg = JSON.parse(value);
  assert.equal(msg.id, id, `${method} reply carries its request id`);
  return msg;
}
const tool = async (name, path) => (await call("tools/call", { name, arguments: { path } })).result;

const checks = [];
const check = (name, fn) => checks.push([name, fn]);

check("initialize echoes protocolVersion and names the server", async () => {
  const version = JSON.parse(readFileSync(repo("plugins/tutor/.claude-plugin/plugin.json"), "utf8")).version;
  const msg = await call("initialize", {
    protocolVersion: "2025-06-18",
    capabilities: { extensions: { "io.modelcontextprotocol/ui": { mimeTypes: ["text/html;profile=mcp-app"] } } },
    clientInfo: { name: "check-host", version: "9.9" },
  });
  assert.deepEqual(msg.result, {
    protocolVersion: "2025-06-18",
    capabilities: { tools: {}, resources: {} },
    serverInfo: { name: "tutor", version },
  });
});

check("initialize logs the client and its MCP Apps capability to stderr", async () => {
  assert.equal(
    (await errLines.next()).value,
    'tutor: client check-host 9.9, io.modelcontextprotocol/ui: {"mimeTypes":["text/html;profile=mcp-app"]}',
  );
});

check("notifications get no reply", async () => {
  child.stdin.write(JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }) + "\n");
  assert.deepEqual((await call("ping")).result, {});
});

check("server/discover gets -32601", async () => {
  assert.equal((await call("server/discover", {})).error.code, -32601);
});

check("tools/list has exactly show_lesson and read_lesson with their _meta", async () => {
  const { tools } = (await call("tools/list", {})).result;
  assert.deepEqual(
    tools.map((t) => [t.name, t._meta]),
    [
      ["show_lesson", { ui: { resourceUri: "ui://tutor/lesson" }, "ui/resourceUri": "ui://tutor/lesson" }],
      ["read_lesson", { ui: { visibility: ["app"] } }],
    ],
  );
  for (const t of tools) assert.deepEqual(t.inputSchema.required, ["path"], `${t.name} requires path`);
});

check("resources/list lists ui://tutor/lesson as an MCP App", async () => {
  const { resources } = (await call("resources/list", {})).result;
  assert.deepEqual(
    resources.map((r) => [r.uri, r.mimeType]),
    [["ui://tutor/lesson", "text/html;profile=mcp-app"]],
  );
});

check("resources/read returns the shell with head.html, the panel script and the jsdelivr CSP", async () => {
  const { contents } = (await call("resources/read", { uri: "ui://tutor/lesson" })).result;
  assert.equal(contents.length, 1, "one content item");
  const [c] = contents;
  assert.equal(c.uri, "ui://tutor/lesson");
  assert.equal(c.mimeType, "text/html;profile=mcp-app");
  assert.deepEqual(c._meta, { ui: { csp: { resourceDomains: ["https://cdn.jsdelivr.net"] }, prefersBorder: true } });
  assert.ok(c.text.startsWith("<!doctype html>\n"), "shell starts with head.html's first line");
  const panel = readFileSync(repo("plugins/tutor/server/panel.js"), "utf8");
  assert.ok(c.text.includes(`<title>Lesson</title>\n<script>\n${panel}</script>`), "shell holds the panel script");
});

check("resources/read of an unknown uri is an error", async () => {
  assert.equal((await call("resources/read", { uri: "ui://tutor/nope" })).error.code, -32002);
});

check("show_lesson returns only the file:// link", async () => {
  assert.deepEqual(await tool("show_lesson", lesson), { content: [{ type: "text", text: `file://${lesson}` }] });
});

check("read_lesson inlines the svg as a data URI and changes nothing else", async () => {
  const { html } = (await tool("read_lesson", lesson)).structuredContent;
  const [, b64] = html.match(/src="data:image\/svg\+xml;base64,([^"]*)"/) ?? [];
  assert.ok(b64, "img src became a data:image/svg+xml;base64, URI");
  assert.ok(Buffer.from(b64, "base64").equals(readFileSync(svg)), "data URI decodes to img/02-per-hundred.svg's bytes");
  assert.ok(!html.includes('src="img/'), 'no relative src="img/ remains');
  assert.equal(
    html.replace(`data:image/svg+xml;base64,${b64}`, "img/02-per-hundred.svg"),
    readFileSync(lesson, "utf8"),
    "rest of the page is byte-identical",
  );
});

check("bad paths return isError with a one-line reason", async () => {
  assert.deepEqual(await tool("show_lesson", "02-percent-of-a-number.html"), {
    content: [{ type: "text", text: "path must be absolute: 02-percent-of-a-number.html" }],
    isError: true,
  });
  assert.deepEqual(await tool("read_lesson", `${lessonDir}/goal.md`), {
    content: [{ type: "text", text: `path must be a .html lesson page: ${lessonDir}/goal.md` }],
    isError: true,
  });
  assert.deepEqual(await tool("show_lesson", `${lessonDir}/99-missing.html`), {
    content: [{ type: "text", text: `no file at ${lessonDir}/99-missing.html` }],
    isError: true,
  });
});

let failed = 0;
for (const [name, fn] of checks) {
  try {
    await fn();
    console.log(`ok   ${name}`);
  } catch (e) {
    failed++;
    console.log(`FAIL ${name}\n     ${e.message.split("\n").join("\n     ")}`);
  }
}
child.stdin.end();
console.log(failed ? `${failed} of ${checks.length} checks failed` : `all ${checks.length} checks passed`);
process.exitCode = failed ? 1 : 0;
