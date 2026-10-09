# Claude-only rules

These rules add to SKILL.md when a Claude tool is there. Each section names the tool it needs; skip a section when that tool is missing. The files stay the record, and grading and typed chat answers do not change.

## At step 2: the inbox

Only when goal.md has a `Page:` link and the `ArtifactData` tool is available. A lesson page on the link has an answer box under each open question, and its Save writes to the artifact's database.

- Before chat answers, list the collection `data/users/me` with `ArtifactData` at that link.
- A document with `lesson`, `q`, `text` and `tag` is a chat answer for that lesson's page: `{q: "Q2", text: "b", tag: "sure"}` is `2: b sure`, R1 is `r1`, G is `g`, and a question marked to redo is `2 again`. A `<lesson>-done` document is `done`. Record them by step 2 as usual, word for word. Leave other documents alone.
- After the file is written, delete the documents you copied, in one `batch`, each pinned to the version you read.
- When grading asks for a redo, add `data-redo` to that question's `<section>`, so the page shows a new box under the feedback. Remove it once the redo is graded.

## A run with no learner message

Only when goal.md has a `Page:` link and the `ArtifactData` tool is available. A daily scheduled task can start a run with only the command, and nobody there to answer. Then, for each goal folder with a `Page:` link, list its inbox. For each lesson with a `<lesson>-done` document, do the inbox step, grade that lesson, update goal.md, write the next lesson after a pass, and publish. Change nothing else: record no answers without a Done mark, ask nothing and start no goal. End with one line per goal graded, or say in one line that nothing was marked done, with each goal's link.

## At step 5: publish

Only when the `Artifact` tool is available. Each goal is one private artifact, and its link is the `- Page:` line in goal.md, after `- Help:`. The learning folder stays the record: the artifact is a copy of it.

- **First publish.** Copy `site/` from this skill's folder to `<goal>/.site/`. Publish `.site/index.html` as the page, with `root` set to the goal folder, `title` set to the goal's name, `icon` set to `lesson` and `capabilities: {db: {}, user: {}}`. Send `.site/answers.js` as `answers.js`, and `goal.md` (as `text/plain`), every lesson and review page and every picture as files at their own paths. Then add `- Page: <link>` to goal.md; the copy on the page gets it with the next publish.
- **Later runs.** In a session that has not published to the link yet, read it once and list its files (`scope: "files"`), since the tool refuses to change a path it has not seen. Then publish `.site/index.html` to the link with only the files this run wrote or changed, goal.md included.
- **Review pages.** When you write `review-<date>.html`, add it to the end of the Plan as `- [Review <date>](review-<date>.html)`, and give it the status `graded` once graded, so the home page can find it.
- **Design.** The home page reads goal.md and draws itself, and `head.html` styles the lessons. Write no HTML for the home page and do not restyle a page.
- **Terminal line.** Give the link in place of the `file://` path. An open page reloads by itself after a publish and lands on the home page.

If a publish fails, give the `file://` path as usual and say why in the terminal line.

## The answer card

Only when the `show_widget` tool is available. Load its guide first, as the tool asks, with the `interactive` module.

After a run writes a lesson or review page, or grades one with a redo, show one card in the chat. It holds the questions on that page that wait for an answer and take a letter or a number: review questions, lesson questions and the guess. Open questions stay typed in the chat. With no such question, show no card. Show it after the file is written and before the terminal line.

Copy the card below and change only `title` and `qs`. Each question is `[prefix, text, options]`, in page order:

- The prefix is what the learner would type: `r1` for R1, `2` for Q2, `g` for the guess, `2 again` for a question marked to redo.
- The text is the question word for word, label included (`R1.`, `Q2.`, `Guess.`). Write math as plain text, like x² or 1/2, not TeX.
- The options are the option texts word for word, without their letters. Leave them out for a number question.

A tap sends one chat answer, like `2: b sure` or `r1: 42 guess`, and Done sends `done`. Record them by step 2 as usual. The card never holds which option is right, so never add it, in any form.

```html
<h2 class="sr-only">Answer card</h2>
<div id="c" style="background: var(--surface-2); border: 0.5px solid var(--border); border-radius: 12px; padding: 1rem 1.25rem;"></div>
<script>
const title = "04 Adding and overflow";
const qs = [
  ["2", "Q2. 01110000 + 00110000 in 8-bit two's complement is", ["160", "-96", "96", "32"]],
  ["3", "Q3. 11111110 + 00000011 is what number?"],
];
let tag = "sure";
const c = document.getElementById("c");
const el = (t, css, text) => { const e = document.createElement(t); e.style.cssText = css; e.textContent = text ?? ""; return e; };
const send = (b, m) => { sendPrompt(m); b.textContent += " · sent"; b.style.background = "var(--surface-1)"; };
c.append(el("p", "font-weight: 500; margin: 0 0 12px", title));
for (const [p, text, opts] of qs) {
  const d = el("div", "margin: 0 0 16px");
  d.append(el("p", "margin: 0 0 8px", text));
  if (opts) opts.forEach((o, i) => {
    const b = el("button", "display: block; text-align: left; margin: 0 0 6px", `${"abcdef"[i]}) ${o} ↗`);
    b.onclick = () => send(b, `${p}: ${"abcdef"[i]} ${tag}`);
    d.append(b);
  });
  else {
    const box = el("input", "width: 120px"), b = el("button", "margin-left: 8px", "Send ↗"), err = el("p", "font-size: 13px; color: var(--text-danger); margin: 4px 0 0");
    box.oninput = () => err.textContent = "";
    b.onclick = () => box.value.trim() ? send(b, `${p}: ${box.value.trim()} ${tag}`) : err.textContent = "Enter an answer first";
    d.append(box, b, err);
  }
  c.append(d);
}
const foot = el("div", "display: flex; gap: 8px; border-top: 0.5px solid var(--border); padding-top: 12px");
const tb = el("button", "", "Tag: sure"), done = el("button", "margin-left: auto", "Done ↗");
tb.onclick = () => { tag = tag == "sure" ? "guess" : "sure"; tb.textContent = "Tag: " + tag; };
done.onclick = () => send(done, "done");
foot.append(tb, done);
c.append(foot);
</script>
```
