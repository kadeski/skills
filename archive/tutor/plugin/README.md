# tutor

`tutor` is a Claude skill that teaches one goal at a time on one claude.ai page per goal. Lessons are short: a picture, few words, and questions. Some lessons add a small control you can move to see the idea change. You answer on the page and press Done to have your answers graded, and the rules you pass come back later as spaced review. The page works on desktop and phone. Use it to learn or practice a topic over several sessions.

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

In Claude Code the command is `/tutor:tutor`. The tutor makes a private page titled `Tutor: <goal>` and gives you its link. Run `/tutor` again to continue: it finds your goal pages by that title, or give it a page's link. Goals from tutor 2.x, kept in folders with a `goal.md`, do not carry over yet ([issue 49](https://github.com/kadeski/skills/issues/49)).

On the page:

- Tap an option or type in the box under each question. Your answers save as you go, and you can change them until you press Done.
- Stuck? Comment on the question and send it to Claude: ask for a hint or the answer, or say the lesson is too easy or too hard. The tutor writes a hint or the answer under the question and replies in the comment. On a phone, turn on Send to Claude before you post.
- Done locks your answers and sends them to the tutor. Feedback appears under each answer without a reload. A question to redo opens again under its feedback.

If a Claude Code session is watching the page with auto-replies armed (the last line of its `/tutor` run says so), Done and comments sent to Claude from a desktop browser reach it at once. A comment sent from a phone is usually answered by Claude on its own, without the tutor: the hint or answer reaches the page at the next `/tutor` run. Anything else waits, and the next `/tutor` run handles it. You can also ask in the chat: for a hint, to see the answer, too easy, too hard, or done.

## License

MIT. See [LICENSE](LICENSE).
