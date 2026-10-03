# skills

Agent skills by Kaden Staker. They work in Claude Code, Codex, Cursor, Gemini CLI, Grok Build and any agent that reads `SKILL.md` files.

Each plugin lives in `plugins/<name>/` and has its own README with install steps for every agent. In Claude Code, add this repo as a marketplace once, then install the plugins you want:

```
/plugin marketplace add kadeski/skills
/plugin install <plugin>@kadeski
```

## Plugins

- [tutor](plugins/tutor/README.md): teaches one goal at a time in HTML pages you read in the browser. Short lessons are graded when you say `done`, and the rules you pass come back later as spaced review.

## License

MIT. See [LICENSE](LICENSE).
