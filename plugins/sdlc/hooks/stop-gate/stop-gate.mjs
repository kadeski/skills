#!/usr/bin/env node
// Stop and TaskCompleted hook: Claude can't finish a turn, or tick a task, while the project's checks fail.
//
// Usage (command hook on the Stop and TaskCompleted events):
//   node stop-gate.mjs                 runs the commands in the repo's .claude/checks.json
//   node stop-gate.mjs "npm test"      runs this command instead, on both events
//
// .claude/checks.json: { "stop": "<full checks>", "task": "<narrower checks, optional>" }
// Stop runs `stop`. TaskCompleted runs `task`, or `stop` when there is no `task`.
// No argument and no checks file: does nothing, so a hook from a plugin leaves other repos alone.
//
// - Checks the checkout the session started in, plus every other checkout of the same repo
//   (a worktree elsewhere) that the session edited with Edit, Write, MultiEdit or NotebookEdit,
//   as read from its transcript and its subagents' transcripts. Edits made through Bash are not seen.
//   Each checkout uses its own checks file and its own state.
// - Runs a check only when the working tree changed since that check's last green run,
//   so chat-only turns stay fast. Fingerprint = git tree of all tracked + untracked
//   (non-ignored) files, built in a throwaway index so the real index is untouched.
//   Each check command keeps its own green tree, so a green `task` run never skips `stop`.
// - STOP_GATE_REQUIRES names a path, relative to the checkout root, that must exist before the
//   gate runs there (e.g. node_modules). A checkout without it is skipped.
// - On failure, Stop gets JSON `decision: "block"` with the output tail; TaskCompleted gets
//   exit 2 with the tail on stderr.
// - Blocks at most MAX_BLOCKS times per Stop turn of one session, or per task. Then it lets
//   Claude through, warns the user, and stays quiet for that check until the files change again.
// - Not a git repo: does nothing.

import { spawnSync } from 'node:child_process';
import {
  readFileSync, writeFileSync, renameSync, copyFileSync, existsSync, mkdtempSync, readdirSync, realpathSync,
  rmSync, statSync, utimesSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';

const MAX_BLOCKS = Number(process.env.STOP_GATE_MAX_BLOCKS || 3);
const TIMEOUT_MS = Number(process.env.STOP_GATE_TIMEOUT_SEC || 540) * 1000; // under the hook's 600 s default
const REQUIRES = (process.env.STOP_GATE_REQUIRES || '').trim();
const TAIL_LINES = 60;
const DAY_MS = 24 * 60 * 60 * 1000;
const EDIT_TOOLS = new Set(['Edit', 'Write', 'MultiEdit', 'NotebookEdit']);

let input = {};
try { input = JSON.parse(readFileSync(0, 'utf8') || '{}'); } catch { /* no stdin: run with defaults */ }
const isTask = input.hook_event_name === 'TaskCompleted';
const event = isTask ? 'task' : 'stop';

const git = (cwd, args, opts = {}) => spawnSync('git', args, { cwd, encoding: 'utf8', maxBuffer: 64 << 20, ...opts });
const gitPath = (root, name) => resolve(root, git(root, ['rev-parse', '--git-path', name]).stdout.trim());

// The checkout holding `dir`, and its repo's common git dir (shared by all its worktrees).
function repoOf(dir) {
  // No --path-format=absolute: git before 2.31 echoes it back as output.
  const r = git(dir, ['rev-parse', '--show-toplevel', '--git-common-dir']);
  if (r.status !== 0) return null;
  const [root, common] = r.stdout.trim().split('\n');
  if (!root || !common) return null;
  try { return { root, common: realpathSync(resolve(dir, common)) }; } catch { return null; }
}

const start = input.cwd || process.env.CLAUDE_PROJECT_DIR || process.cwd();
const home = repoOf(start);
if (!home) process.exit(0);

// The main transcript and every subagent transcript under <session>/subagents/.
function transcripts(path) {
  if (typeof path !== 'string' || !path) return [];
  const out = [path];
  const walk = (dir) => {
    let entries;
    try { entries = readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      const p = join(dir, e.name);
      if (e.isDirectory()) walk(p);
      else if (e.name.endsWith('.jsonl')) out.push(p);
    }
  };
  if (path.endsWith('.jsonl')) walk(join(path.slice(0, -'.jsonl'.length), 'subagents'));
  return out;
}

function editedFiles() {
  const files = new Set();
  for (const t of transcripts(input.transcript_path)) {
    let text;
    try { text = readFileSync(t, 'utf8'); } catch { continue; }
    for (const line of text.split('\n')) {
      if (!line.includes('"tool_use"') || !line.includes('_path"')) continue;
      let rec;
      try { rec = JSON.parse(line); } catch { continue; }
      const content = rec?.message?.content;
      if (!Array.isArray(content)) continue;
      for (const c of content) {
        if (c?.type !== 'tool_use' || !EDIT_TOOLS.has(c.name)) continue;
        const f = c.input?.file_path ?? c.input?.notebook_path;
        if (typeof f === 'string' && f) files.add(resolve(start, f));
      }
    }
  }
  return files;
}

// The start checkout first, then other checkouts of the same repo that the session edited.
function checkouts() {
  const roots = [home.root];
  const seen = new Set();
  for (const file of editedFiles()) {
    let dir = dirname(file);
    while (!existsSync(dir) && dirname(dir) !== dir) dir = dirname(dir); // deleted file or worktree
    if (seen.has(dir)) continue;
    seen.add(dir);
    const r = repoOf(dir);
    if (r && r.common === home.common && !roots.includes(r.root)) roots.push(r.root);
  }
  return roots;
}

function checkCommand(root) {
  const arg = process.argv.slice(2).join(' ').trim();
  if (arg) return arg;
  let file;
  try { file = JSON.parse(readFileSync(join(root, '.claude', 'checks.json'), 'utf8')); } catch { return ''; }
  const pick = (v) => (typeof v === 'string' ? v.trim() : '');
  return (isTask && pick(file?.task)) || pick(file?.stop);
}

function fingerprint(root) {
  const tmp = mkdtempSync(join(tmpdir(), 'stop-gate-'));
  try {
    const idx = join(tmp, 'index');
    const real = gitPath(root, 'index');
    if (existsSync(real)) {
      copyFileSync(real, idx); // reuse the stat cache: fast on big repos
      // Keep the index's own time (rounded down) on the copy. git trusts a cached entry only when
      // the file is older than the index, so a copy stamped "now" hides a same-size edit made in
      // the second the index was written.
      const at = Math.floor(statSync(real).mtimeMs / 1000);
      utimesSync(idx, at, at);
    }
    const env = { ...process.env, GIT_INDEX_FILE: idx };
    if (git(root, ['add', '-A'], { env }).status !== 0) return null;
    const tree = git(root, ['write-tree'], { env });
    return tree.status === 0 ? tree.stdout.trim() : null;
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
}

// State, one file per checkout in its git dir:
// { checks: { <command>: { green, gaveUp: { stop, task } } },
//   turns: { <session>: { blocks, at } }, tasks: { <session:task>: { blocks, at } } }
// Counts live in the start checkout's file. Each change re-reads the file, so a session whose
// check ran for minutes doesn't write back a stale copy over another session's counts.
function readState(path) {
  let s;
  try { s = JSON.parse(readFileSync(path, 'utf8')); } catch { /* first run */ }
  if (typeof s !== 'object' || s === null || typeof s.checks !== 'object' || s.checks === null) {
    s = { checks: {} }; // first run, or the older single-command format
  }
  delete s.turn; // the older single-slot turn count
  for (const k of ['turns', 'tasks']) if (typeof s[k] !== 'object' || s[k] === null) s[k] = {};
  return s;
}
function updateState(path, change) {
  const s = readState(path);
  change(s);
  // Drop counts older than a day (turns and tasks never retried). Not by session: agent-team
  // teammates are separate sessions in one checkout, and their hooks interleave.
  for (const k of ['turns', 'tasks']) {
    for (const key of Object.keys(s[k])) if (!(Date.now() - (s[k][key]?.at ?? 0) < DAY_MS)) delete s[k][key];
  }
  const tmp = `${path}.${process.pid}.tmp`;
  writeFileSync(tmp, JSON.stringify(s, null, 2));
  renameSync(tmp, path);
}
const gaveUpOf = (check) => (typeof check?.gaveUp === 'object' && check.gaveUp !== null ? check.gaveUp : {});

const results = [];
for (const root of checkouts()) {
  const cmd = checkCommand(root);
  if (!cmd) continue;
  if (REQUIRES && !existsSync(resolve(root, REQUIRES))) continue;
  const statePath = gitPath(root, 'claude-stop-gate.json');
  const check = readState(statePath).checks[cmd];
  const fp = fingerprint(root);
  if (fp && (fp === check?.green || fp === gaveUpOf(check)[event])) continue;
  const run = spawnSync(cmd, { cwd: root, shell: true, encoding: 'utf8', maxBuffer: 64 << 20, timeout: TIMEOUT_MS });
  results.push({ root, cmd, statePath, fp, run, ok: run.status === 0 && !run.error });
}
if (!results.length) process.exit(0);

for (const r of results.filter((r) => r.ok)) updateState(r.statePath, (s) => { s.checks[r.cmd] = { green: r.fp }; });

// Stop counts blocks within one turn of one session (stop_hook_active says Claude is continuing
// after a block). TaskCompleted has no such flag, so it counts refusals per task.
const homeState = gitPath(home.root, 'claude-stop-gate.json');
const counts = isTask ? 'tasks' : 'turns';
const key = isTask ? `${input.session_id}:${input.task_id}` : String(input.session_id);
const failures = results.filter((r) => !r.ok);
if (!failures.length) {
  updateState(homeState, (s) => { delete s[counts][key]; });
  process.exit(0);
}

let blocks;
updateState(homeState, (s) => {
  const prev = s[counts][key]?.blocks || 0;
  blocks = isTask || input.stop_hook_active ? prev + 1 : 1;
  if (blocks > MAX_BLOCKS) delete s[counts][key];
  else s[counts][key] = { blocks, at: Date.now() };
});

const where = (f) => (f.root === home.root ? '' : ` in ${f.root}`);
const named = failures.map((f) => `\`${f.cmd}\`${where(f)}`).join(', ');

if (blocks > MAX_BLOCKS) {
  // Giving up is per event: a task let through after 3 refusals must not also silence the Stop
  // gate when both run the same command (a checks file with no `task`).
  for (const f of failures) {
    updateState(f.statePath, (s) => {
      const check = (s.checks[f.cmd] ??= {});
      check.gaveUp = { ...gaveUpOf(check), [event]: f.fp };
    });
  }
  const what = isTask ? `The task "${input.task_subject || input.task_id}" was let through` : 'Claude was allowed to stop';
  console.log(JSON.stringify({
    systemMessage: `stop-gate: ${named} still ${failures.length > 1 ? 'fail' : 'fails'} after ${MAX_BLOCKS} tries. ${what}; check it yourself. The gate stays quiet until files change.`,
  }));
  process.exit(0);
}

const why = ({ run }) => (run.error
  ? `did not finish (${run.error.code === 'ETIMEDOUT' ? `timed out after ${TIMEOUT_MS / 1000} s` : run.error.message})`
  : `exited ${run.status}`);
const tail = ({ run }) => `${run.stdout || ''}${run.stderr || ''}`.replace(/\x1b\[[0-9;]*m/g, '')
  .trimEnd().split(/\r?\n/).slice(-TAIL_LINES).join('\n').slice(-8000);
const finish = isTask ? 'marking the task completed' : 'finishing';
const reason =
  `Checks failed: ${failures.map((f) => `\`${f.cmd}\`${where(f)} ${why(f)}`).join('; ')} (stop-gate, try ${blocks} of ${MAX_BLOCKS}).\n` +
  `Fix the cause and run the checks again before ${finish}. Don't skip, weaken or delete tests to get green. ` +
  `If the failure isn't from your change or you can't fix it, stop and tell the user plainly what fails and why.\n\n` +
  failures.map((f) => `Last ${TAIL_LINES} lines of output${where(f) && ` from ${f.root}`}:\n${tail(f)}`).join('\n\n');

if (isTask) {
  // Exit 2 blocks the completion and feeds stderr back to Claude. Something on stdout keeps
  // Claude Code from reading a "No such file or directory" in the tail as a broken hook.
  console.log(`stop-gate: checks failed (try ${blocks} of ${MAX_BLOCKS})`);
  console.error(reason);
  process.exit(2);
}
console.log(JSON.stringify({ decision: 'block', reason }));
process.exit(0);
