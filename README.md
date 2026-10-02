# skills

Agent skills by Kaden Staker. They work in Claude Code, Codex, Cursor, Gemini CLI, Grok Build and any agent that reads `SKILL.md` files.

## Install

Pick one way per agent. Installing more than one way in the same agent gives you every skill twice.

<details>
<summary><strong>Claude Code</strong></summary>

```
/plugin marketplace add kadeski/skills
/plugin install kadeski-skills@kadeski
```

Skills run as `/kadeski-skills:<skill>`, for example `/kadeski-skills:tutor`.

If you installed the old `tutor@kadeski` plugin, remove it first: `/plugin uninstall tutor@kadeski`.

</details>

<details>
<summary><strong>Codex</strong></summary>

```bash
codex plugin marketplace add kadeski/skills
codex plugin add kadeski-skills@kadeski
```

</details>

<details>
<summary><strong>Gemini CLI</strong></summary>

```bash
gemini extensions install https://github.com/kadeski/skills
```

</details>

<details>
<summary><strong>Cursor</strong></summary>

The repo is a Cursor plugin (`.cursor-plugin/plugin.json`). A team admin can add it under **Dashboard -> Plugins -> Add Marketplace -> Import from Repo**. On your own, use the installer under "Any other agent". Not tested yet.

</details>

<details>
<summary><strong>Grok Build</strong></summary>

Grok Build reads Claude Code marketplaces, so add `kadeski/skills` as a marketplace source and install `kadeski-skills` from its Marketplace tab. Not tested yet.

</details>

<details>
<summary><strong>Any other agent</strong></summary>

```bash
npx skills@latest add kadeski/skills
```

This copies the skill files into your project, so you can edit them. Update with `npx skills update`.

</details>

## Skills

- [tutor](docs/tutor.md): teaches one goal at a time in plain markdown files. Short lessons are graded when you say `done`, and the rules you pass come back later as spaced review.

## License

MIT. See [LICENSE](LICENSE).
