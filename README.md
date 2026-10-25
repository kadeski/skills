# skills

Agent skills by Kaden Staker. Each plugin says below which agents it works in: Claude Code only, or also Codex, Cursor, Gemini CLI, Grok Build and any agent that reads `SKILL.md` files.

Each plugin lives in `plugins/<name>/` and has its own README with install steps for the agents it supports. In Claude Code, add this repo as a marketplace once, then install the plugins you want:

```
/plugin marketplace add kadeski/skills
/plugin install <plugin>@kadeski
```

## Plugins

- [doc-lint](plugins/doc-lint/README.md) (Claude Code only): audits a project's plan and design docs for broken links, stale numbers, contradictions between files, statuses that disagree with where the work is tracked and open work tracked nowhere, and reports the findings without fixing them.
- [study](plugins/study/README.md) (Claude Code only): teaches one goal across sessions in the chat. It finds where your understanding ends, plans the shortest path, teaches one step at a time with a check after each, runs practice later and keeps a knowledge graph of what you were taught.
- [tutor](plugins/tutor/README.md) (Claude Code only): teaches one goal at a time on one claude.ai page per goal. You answer on the page, Done sends your answers to be graded, and the rules you pass come back later as spaced review.

## License

MIT. See [LICENSE](LICENSE).
