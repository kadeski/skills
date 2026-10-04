# tutor

`tutor` is an agent skill that teaches one goal at a time, as HTML pages you read in any browser. Lessons are short: a picture, few words, and questions. Some lessons add a small control you can move to see the idea change. Your answers are graded when you say `done`, and the rules you pass come back later as spaced review. Say `stuck`, `too easy`, `too hard` or `just tell me` any time. Use it to learn or practice a topic over several sessions.

## Install

Pick one way per agent. Installing more than one way in the same agent gives you the skill twice.

<details>
<summary><strong>Claude Code</strong></summary>

```
/plugin marketplace add kadeski/skills
/plugin install tutor@kadeski
```

If you installed `kadeski-skills@kadeski`, remove it first: `/plugin uninstall kadeski-skills@kadeski`.

</details>

<details>
<summary><strong>Codex</strong></summary>

```bash
codex plugin marketplace add kadeski/skills
codex plugin add tutor@kadeski
```

If you installed `kadeski-skills@kadeski`, remove it first: `codex plugin remove kadeski-skills@kadeski`.

</details>

<details>
<summary><strong>Gemini CLI</strong></summary>

```bash
gemini skills install https://github.com/kadeski/skills --path plugins/tutor/skills/tutor
```

If you installed the `kadeski-skills` extension, remove it first: `gemini extensions uninstall kadeski-skills`.

</details>

<details>
<summary><strong>Cursor</strong></summary>

The repo is a Cursor marketplace (`.cursor-plugin/marketplace.json`). A team admin can add it under **Dashboard -> Plugins -> Add Marketplace -> Import from Repo**. On your own, use the installer under "Any other agent". Not tested yet.

</details>

<details>
<summary><strong>Grok Build</strong></summary>

Grok Build reads Claude Code marketplaces, so add `kadeski/skills` as a marketplace source and install `tutor` from its Marketplace tab. Not tested yet.

</details>

<details>
<summary><strong>Any other agent</strong></summary>

```bash
npx skills@latest add kadeski/skills --skill tutor
```

This copies the skill files into your project, so you can edit them. Update with `npx skills update`.

</details>

## Usage

```
/tutor <topic> [source: path or url]
```

In Claude Code the command is `/tutor:tutor`. In other agents, ask for the tutor skill by name.

Start your agent in the folder you want to learn in: each goal gets its own folder there. Each lesson is an HTML page. The tutor gives its path after each run: open it in any browser, and refresh it after grading. A host that draws MCP Apps, such as Claude's Cowork, also shows the lesson in the chat, if Node.js is installed. Cursor and the Codex app draw them too, but are not tested yet. The browser works everywhere.

Answer in the chat: `1: ...` for Q1, `g: c` for the guess, `2 again: ...` for a redo. Type or dictate, in one message or several. The tutor copies each answer into the lesson as you wrote it.

Phones are not supported yet: a phone's file preview does not load the lesson's pictures.

Lessons from tutor 1.x are markdown files. An open one is graded as it is, and the next lesson is an HTML page.

## License

MIT. See [LICENSE](LICENSE).
