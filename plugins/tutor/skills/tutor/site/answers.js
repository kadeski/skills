// tutor answer boxes. On claude.ai, a lesson page saves what the learner types to
// the artifact's database, and the next run copies it into the lesson file.
// Anywhere else (file://, no database, signed out) it does nothing.
(async () => {
  if (!window.claude || !window.claude.use) return;
  const [db, user] = await Promise.all([claude.use("db"), claude.use("user")]);
  const uid = db && user ? await user.id() : null;
  const lesson = decodeURIComponent(location.pathname.split("/").pop() || "").replace(/\.html$/, "");
  if (!uid || !lesson || lesson == "index") return;
  const inbox = db.collection("data/users/" + uid);
  const sections = [...document.querySelectorAll("section[id]")].filter(s => !s.querySelector("pre.answer") || s.hasAttribute("data-redo"));
  if (!sections.length) return;

  const style = document.createElement("style");
  style.textContent = `
section:has(.tutor-box)::after { display: none; }
.tutor-box { display: grid; gap: .5rem; margin-top: .75rem; }
.tutor-box textarea { width: 100%; box-sizing: border-box; min-height: 3.2rem; padding: .5rem .7rem; font: .95rem/1.5 system-ui, sans-serif; color: var(--fg); background: var(--soft); border: 1px solid var(--line); border-radius: 8px; resize: vertical; }
.tutor-row { display: flex; flex-wrap: wrap; gap: .5rem; align-items: center; }
.tutor-row button[aria-pressed="true"] { border-color: var(--blue); color: var(--blue); }
.tutor-row .save { margin-left: auto; }
.tutor-note { font-size: .8rem; color: var(--muted); }`;
  document.head.append(style);

  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text) e.textContent = text; return e; };
  const time = iso => new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });

  for (const s of sections) {
    const ref = inbox.doc(`${lesson}-${s.id}`);
    const box = el("div", "tutor-box"), text = el("textarea"), row = el("div", "tutor-row"), note = el("span", "tutor-note");
    text.id = "answer-" + s.id;
    text.placeholder = s.hasAttribute("data-redo") ? "Your new answer" : "Your answer";
    let tag = "sure";
    const tags = ["sure", "guess"].map(t => { const b = el("button", "", t); b.type = "button"; b.onclick = () => { tag = t; paint(); }; return b; });
    const paint = () => tags.forEach(b => b.setAttribute("aria-pressed", b.textContent == tag));
    const save = el("button", "save", "Save");
    save.type = "button";
    save.onclick = async () => {
      const value = text.value.trim();
      if (!value) { note.textContent = "Write an answer first."; return; }
      save.disabled = true;
      try {
        const savedAt = new Date().toISOString();
        await ref.set({ lesson, q: s.id, text: value, tag, savedAt });
        note.textContent = `Saved ${time(savedAt)}. Say done in Claude Code to grade it.`;
      } catch (e) {
        note.textContent = "Could not save: " + (e.code || e.message);
      }
      save.disabled = false;
    };
    text.oninput = () => { note.textContent = ""; };
    paint();
    row.append(...tags, save);
    box.append(text, row, note);
    s.append(box);
    ref.get().then(d => {
      const v = d.exists && d.data();
      if (!v || text.value) return;
      text.value = v.text || "";
      tag = v.tag == "guess" ? "guess" : "sure";
      paint();
      note.textContent = `Saved ${time(v.savedAt)}. Say done in Claude Code to grade it.`;
    }, () => {});
  }

  const done = el("button", "", "Done"), doneNote = el("span", "tutor-note"), doneRow = el("p", "tutor-row");
  done.type = "button";
  done.onclick = async () => {
    try {
      await inbox.doc(`${lesson}-done`).set({ lesson, done: true, savedAt: new Date().toISOString() });
      doneNote.textContent = "Marked done. Say done in Claude Code to grade it.";
    } catch (e) {
      doneNote.textContent = "Could not save: " + (e.code || e.message);
    }
  };
  doneRow.append(done, doneNote);
  [...document.querySelectorAll("section[id]")].pop().after(doneRow);
})();
