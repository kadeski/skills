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
// - Runs a check only when the working tree changed since that check's last green run,
//   so chat-only turns stay fast. Fingerprint = git tree of all tracked + untracked
//   (non-ignored) files, built in a throwaway index so the real index is untouched.
//   Each check command keeps its own green tree, so a green `task` run never skips `stop`.
// - On failure, Stop gets JSON `decision: "block"` with the output tail; TaskCompleted gets
//   exit 2 with the tail on stderr.
// - Blocks at most MAX_BLOCKS times per Stop turn, or per task. Then it lets Claude through,
//   warns the user, and stays quiet for that check until the files change again.
// - Not a git repo: does nothing.

import { spawnSync } from 'node:child_process';
import { readFileSync, writeFileSync, copyFileSync, existsSync, mkdtempSync, rmSync, statSync, utimesSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const MAX_BLOCKS = Number(process.env.STOP_GATE_MAX_BLOCKS || 3);
const TIMEOUT_MS = Number(process.env.STOP_GATE_TIMEOUT_SEC || 540) * 1000; // under the hook's 600 s default
const TAIL_LINES = 60;

let input = {};
try { input = JSON.parse(readFileSync(0, 'utf8') || '{}'); } catch { /* no stdin: run with defaults */ }
const isTask = input.hook_event_name === 'TaskCompleted';

const start = input.cwd || process.env.CLAUDE_PROJECT_DIR || process.cwd();
const top = spawnSync('git', ['rev-parse', '--show-toplevel'], { cwd: start, encoding: 'utf8' });
if (top.status !== 0) process.exit(0);
const root = top.stdout.trim();

function checkCommand() {
  const arg = process.argv.slice(2).join(' ').trim();
  if (arg) return arg;
  let file;
  try { file = JSON.parse(readFileSync(join(root, '.claude', 'checks.json'), 'utf8')); } catch { return ''; }
  const pick = (v) => (typeof v === 'string' ? v.trim() : '');
  return (isTask && pick(file?.task)) || pick(file?.stop);
}
const cmd = checkCommand();
if (!cmd) process.exit(0);

const git = (args, opts = {}) => spawnSync('git', args, { cwd: root, encoding: 'utf8', maxBuffer: 64 << 20, ...opts });
const gitPath = (name) => resolve(root, git(['rev-parse', '--git-path', name]).stdout.trim());

function fingerprint() {
  const tmp = mkdtempSync(join(tmpdir(), 'stop-gate-'));
  try {
    const idx = join(tmp, 'index');
    const real = gitPath('index');
    if (existsSync(real)) {
      copyFileSync(real, idx); // reuse the stat cache: fast on big repos
      // Keep the index's own time (rounded down) on the copy. git trusts a cached entry only when
      // the file is older than the index, so a copy stamped "now" hides a same-size edit made in
      // the second the index was written.
      const at = Math.floor(statSync(real).mtimeMs / 1000);
      utimesSync(idx, at, at);
    }
    const env = { ...process.env, GIT_INDEX_FILE: idx };
    if (git(['add', '-A'], { env }).status !== 0) return null;
    const tree = git(['write-tree'], { env });
    return tree.status === 0 ? tree.stdout.trim() : null;
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
}

// State: { checks: { <command>: { green, gaveUp: { stop, task } } }, turn: { session, blocks }, tasks: { <session:task>: { blocks, at } } }
const statePath = gitPath('claude-stop-gate.json');
let state = {};
try { state = JSON.parse(readFileSync(statePath, 'utf8')); } catch { /* first run */ }
if (typeof state !== 'object' || state === null || typeof state.checks !== 'object' || state.checks === null) {
  state = { checks: {} }; // first run, or the older single-command format
}
state.tasks ??= {};
const save = () => writeFileSync(statePath, JSON.stringify(state, null, 2));
// Drop refusal counts older than a day (tasks never retried). Not by session: agent-team
// teammates are separate sessions in one checkout, and their hooks interleave.
const DAY_MS = 24 * 60 * 60 * 1000;
const stale = Object.keys(state.tasks).filter((k) => !(Date.now() - (state.tasks[k]?.at ?? 0) < DAY_MS));
for (const k of stale) delete state.tasks[k];
if (stale.length) save();

const mine = (state.checks[cmd] ??= {});
// Giving up is per event: a task let through after 3 refusals must not also silence the Stop
// gate when both run the same command (a checks file with no `task`).
const event = isTask ? 'task' : 'stop';
if (typeof mine.gaveUp !== 'object' || mine.gaveUp === null) mine.gaveUp = {};

const fp = fingerprint();
if (fp && (fp === mine.green || fp === mine.gaveUp[event])) process.exit(0);

const run = spawnSync(cmd, { cwd: root, shell: true, encoding: 'utf8', maxBuffer: 64 << 20, timeout: TIMEOUT_MS });
const taskKey = `${input.session_id}:${input.task_id}`;

if (run.status === 0 && !run.error) {
  state.checks[cmd] = { green: fp };
  if (isTask) delete state.tasks[taskKey];
  else delete state.turn;
  save();
  process.exit(0);
}

// Stop counts blocks within one turn (stop_hook_active says Claude is continuing after a block).
// TaskCompleted has no such flag, so it counts refusals per task.
let blocks;
if (isTask) {
  blocks = (state.tasks[taskKey]?.blocks || 0) + 1;
} else {
  const sameTurn = Boolean(input.stop_hook_active) && state.turn?.session === input.session_id;
  blocks = sameTurn ? state.turn.blocks + 1 : 1;
}

if (blocks > MAX_BLOCKS) {
  mine.gaveUp[event] = fp;
  if (isTask) delete state.tasks[taskKey];
  else delete state.turn;
  save();
  const what = isTask ? `The task "${input.task_subject || input.task_id}" was let through` : 'Claude was allowed to stop';
  console.log(JSON.stringify({
    systemMessage: `stop-gate: \`${cmd}\` still fails after ${MAX_BLOCKS} tries. ${what}; check it yourself. The gate stays quiet until files change.`,
  }));
  process.exit(0);
}

if (isTask) state.tasks[taskKey] = { blocks, at: Date.now() };
else state.turn = { session: input.session_id, blocks };
save();

const why = run.error
  ? `did not finish (${run.error.code === 'ETIMEDOUT' ? `timed out after ${TIMEOUT_MS / 1000} s` : run.error.message})`
  : `exited ${run.status}`;
const output = `${run.stdout || ''}${run.stderr || ''}`.replace(/\x1b\[[0-9;]*m/g, '');
const tail = output.trimEnd().split(/\r?\n/).slice(-TAIL_LINES).join('\n').slice(-8000);
const finish = isTask ? 'marking the task completed' : 'finishing';
const reason =
  `Checks failed: \`${cmd}\` ${why} (stop-gate, try ${blocks} of ${MAX_BLOCKS}).\n` +
  `Fix the cause and run the checks again before ${finish}. Don't skip, weaken or delete tests to get green. ` +
  `If the failure isn't from your change or you can't fix it, stop and tell the user plainly what fails and why.\n\n` +
  `Last ${TAIL_LINES} lines of output:\n${tail}`;

if (isTask) {
  // Exit 2 blocks the completion and feeds stderr back to Claude. Something on stdout keeps
  // Claude Code from reading a "No such file or directory" in the tail as a broken hook.
  console.log(`stop-gate: checks failed (try ${blocks} of ${MAX_BLOCKS})`);
  console.error(reason);
  process.exit(2);
}
console.log(JSON.stringify({ decision: 'block', reason }));
process.exit(0);
