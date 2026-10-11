# tutor

`tutor` is an agent skill that teaches one goal at a time, as HTML pages you read in any browser. Lessons are short: a picture, few words, and questions. Some lessons add a small control you can move to see the idea change. Your answers are graded when you say `done`, and the rules you pass come back later as spaced review. Say `stuck`, `too easy`, `too hard` or `just tell me` any time. Use it to learn or practice a topic over several sessions.

## Install

In Claude Code:

```
/plugin marketplace add kadeski/skills
/plugin install tutor@kadeski
```

If you installed `kadeski-skills@kadeski`, remove it first: `/plugin uninstall kadeski-skills@kadeski`.

## Usage

```
/tutor <topic> [source: path or url]
```

In Claude Code the command is `/tutor:tutor`. In other agents, ask for the tutor skill by name.

Start your agent in the folder you want to learn in: each goal gets its own folder there. Each lesson is an HTML page. The tutor gives its path after each run: open it in any browser, and refresh it after grading.

Answer in the chat: `1: ...` for Q1, `g: c` for the guess, `2 again: ...` for a redo. Type or dictate, in one message or several. The tutor copies each answer into the lesson as you wrote it.

Phones are not supported yet: a phone's file preview does not load the lesson's pictures.

Lessons from tutor 1.x are markdown files. An open one is graded as it is, and the next lesson is an HTML page.

## License

MIT. See [LICENSE](LICENSE).
