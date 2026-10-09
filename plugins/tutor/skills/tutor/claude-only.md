# Claude-only rules

These rules add to SKILL.md when a Claude tool is there. Each section names the tool it needs; skip a section when that tool is missing. The files stay the record, and grading and typed chat answers do not change.

## The answer card

Only when the `show_widget` tool is available. Load its guide first, as the tool asks, with the `interactive` module.

After a run writes a lesson or review page, or grades one with a redo, show one card in the chat. It holds the questions on that page that wait for an answer and take a letter or a number: review questions, lesson questions and the guess. Open questions stay typed in the chat. With no such question, show no card. Show it after the file is written and before the terminal line.

Copy the card below and change only `title` and `qs`. Each question is `[prefix, text, options]`, in page order:

- The prefix is what the learner would type: `r1` for R1, `2` for Q2, `g` for the guess, `2 again` for a question marked to redo.
- The text is the question word for word, label included (`R1.`, `Q2.`, `Guess.`). Write math as plain text, like x² or 1/2, not TeX.
- The options are the option texts word for word, without their letters. Leave them out for a number question.

The learner picks an option or types a number for each question, and can switch each one between sure and guess. Send puts every picked answer in one chat message, one per line, like `2: b sure` and `r1: 42 guess`. Send and grade adds `done`. Record them by step 2 as usual. The card never holds which option is right, so never add it, in any form.

```html
<h2 class="sr-only">Answer card</h2>
<div id="c" style="background: var(--surface-2); border: 0.5px solid var(--border); border-radius: 12px; padding: 1rem 1.25rem;"></div>
<script>
const title = "04 Adding and overflow";
const qs = [
  ["2", "Q2. 01110000 + 00110000 in 8-bit two's complement is", ["160", "-96", "96", "32"]],
  ["3", "Q3. 11111110 + 00000011 is what number?"],
];
const el = (t, css, text) => { const e = document.createElement(t); e.style.cssText = css; e.textContent = text ?? ""; return e; };
const c = document.getElementById("c"), picks = {}, note = el("span", "font-size: 13px; color: var(--text-secondary)");
const press = (b, on) => { b.setAttribute("aria-pressed", on); b.style.background = on ? "var(--bg-accent)" : ""; b.style.borderColor = on ? "var(--border-accent)" : ""; };
c.append(el("p", "font-weight: 500; margin: 0 0 12px", title));
for (const [p, text, opts] of qs) {
  const pick = picks[p] = { value: "", tag: "sure" };
  const d = el("div", "margin: 0 0 16px; display: grid; gap: 6px; justify-items: start");
  d.append(el("p", "margin: 0", text));
  if (opts) {
    const bs = opts.map((o, i) => el("button", "text-align: left", `${"abcdef"[i]}) ${o}`));
    bs.forEach((b, i) => b.onclick = () => { pick.value = "abcdef"[i]; note.textContent = ""; bs.forEach(x => press(x, x == b)); });
    d.append(...bs);
  } else {
    const box = el("input", "width: 120px");
    box.oninput = () => { pick.value = box.value.trim(); note.textContent = ""; };
    d.append(box);
  }
  const t = el("button", "font-size: 13px", "sure");
  t.onclick = () => { pick.tag = pick.tag == "sure" ? "guess" : "sure"; t.textContent = pick.tag; press(t, pick.tag == "guess"); };
  d.append(t);
  c.append(d);
}
const foot = el("div", "display: flex; flex-wrap: wrap; gap: 8px; align-items: center; border-top: 0.5px solid var(--border); padding-top: 12px");
const send = el("button", "", "Send ↗"), grade = el("button", "", "Send and grade ↗");
let last = "", graded = false;
const go = withDone => {
  if (graded) { note.textContent = "Already sent for grading"; return; }
  const lines = qs.filter(([p]) => picks[p].value).map(([p]) => `${p}: ${picks[p].value} ${picks[p].tag}`);
  const msg = [...lines, ...(withDone ? ["done"] : [])].join("\n");
  if (!msg) { note.textContent = "Pick an answer first"; return; }
  if (msg == last) { note.textContent = "Already sent"; return; }
  sendPrompt(msg); last = msg; graded = withDone;
  note.textContent = withDone ? "Sent for grading" : "Sent";
};
send.onclick = () => go(false);
grade.onclick = () => go(true);
foot.append(send, grade, note);
c.append(foot);
</script>
```
