# study

`study` is a Claude Code plugin that teaches you one goal across as many sessions as it takes. It first finds out what you already know, then plans the shortest path from there to the goal, then teaches one reasoning step at a time with a check after each step. Later you can practice what you learned, and everything you were taught goes into a knowledge graph that later sessions read.

It works in a normal Claude Code chat: questions come as multiple choice (with a confidence question) or as plain chat. It runs in the terminal, the desktop app and VS Code.

## Install

In Claude Code:

```
/plugin marketplace add kadeski/skills
/plugin install study@kadeski
```

When you enable it, Claude Code asks for a data folder (default `~/Study`). Your goals, answers and knowledge graph are kept there as plain JSON files.

Study needs `python3` (3.9 or newer) on your `PATH`. It uses the standard library only.

To stop Claude Code asking before each Study tool call, allow the whole Study server once, for example in `/permissions`: `mcp__plugin_study_study`.

## Usage

- `/study <goal>` - start a goal, or continue an unfinished one. `/study stop` ends the session for now.
- `/practice [topic]` - practice what you were taught, with problems that don't say which idea they need. `/practice stop` ends it.
- `/graph` - open your knowledge graph as a page in the browser.
- `/import-notes <path>` - add your own notes (markdown, text or PDF) to the knowledge graph.

Claude can also look up what you studied when it would help an answer, without changing anything.

To see the `/study` plan as a task list on models newer than Opus 4.7, Sonnet 4.6 and Haiku 4.5, which leave Claude Code's task tools out by default, start Claude Code with `CLAUDE_CODE_ENABLE_TODO_TOOLS=1 claude` (or set that variable under `env` in `~/.claude/settings.json`).

Pictures and demos are saved in the goal's folder and opened in your browser. If Python Playwright is installed, Claude checks them by rendering them first; otherwise it says it skipped the check.

## License

MIT. See [LICENSE](LICENSE). The method follows ideas from [LearnHarness](https://github.com/amosblomqvist/learnharness); no text or code is copied from it.
