# skills

Agent skills by Kaden Staker. Some plugins work only in Claude Code; the others also work in Codex, Cursor, Gemini CLI, Grok Build and any agent that reads `SKILL.md` files.

Each plugin lives in `plugins/<name>/` and has its own README with install steps for the agents it supports. In Claude Code, add this repo as a marketplace once, then install the plugins you want:

```
/plugin marketplace add kadeski/skills
/plugin install <plugin>@kadeski
```

## Plugins

- [tutor](plugins/tutor/README.md) (Claude Code only): teaches one goal at a time on one claude.ai page per goal. You answer on the page, Done sends your answers to be graded, and the rules you pass come back later as spaced review.

## License

MIT. See [LICENSE](LICENSE).
