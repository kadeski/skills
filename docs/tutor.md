# tutor

`tutor` is an agent skill that teaches one goal at a time, in plain markdown files that open in any markdown app. Lessons are short: a picture, few words, and questions. Your answers are graded when you say `done`, and the rules you pass come back later as spaced review. Say `stuck`, `too easy`, `too hard` or `just tell me` any time. Use it to learn or practice a topic over several sessions.

## Install

See [Install](../README.md#install) for each agent.

## Usage

```
/tutor <topic> [source: path or url]
```

In Claude Code the command is `/kadeski-skills:tutor`. In other agents, ask for the tutor skill by name.

Open the goal folder in an app that edits the files themselves: Obsidian, VS Code, Typora or iA Writer on a computer; Obsidian, iA Writer or Markor on a phone. Not Bear or Joplin: they import notes into their own library, so your answers never reach the files.

## License

MIT. See [LICENSE](../LICENSE).
