/*
 * tutor.js - the fixed behavior of a tutor goal page. Claude designs the page around it;
 * this file does every job that must not break. Do not edit it per goal.
 *
 * VERSION - bump it on every change to this file or to look.css, and also when the meaning of data the
 *   tutor writes changes, since it stands for the skill's version too. The tutor skill keeps the version
 *   each goal page was published with in goal/main.tutorJs and republishes older pages with this file and
 *   look.css, so a newer tutor.js must keep working with pages and documents written for older ones. A
 *   session whose tutor.js is older than the page's leaves the page's requests alone, and the text Done
 *   sends names VERSION, so an older session stops too. A session that cannot use the skill, like Claude
 *   Code's automatic comment reply, writes nothing and says a watching session or a /tutor run grades it.
 *
 * PUBLISH
 *   Copy this file into a scratch folder, since the Artifact tool sends only files under the working or
 *   scratchpad folder. Artifact publish with files: {"tutor.js": "<scratch folder>/tutor.js"} and
 *   capabilities: {db: {rules: [{path: "goal", write: "owner"}, {path: "lessons", write: "owner"}]}, comments: {}}
 *   The page loads it once, at the end of <body>:  <script src="tutor.js"></script>
 *
 * SLOTS - empty elements the page provides; any may be left out.
 *   data-tutor="title"    goal/main title, as text
 *   data-tutor="goal"     goal/main goal line, as text
 *   data-tutor="plan"     the plan; a lesson that exists is a button that shows it
 *   data-tutor="reviews"  rules not yet learned, by next review date
 *   data-tutor="lesson"   the lesson shown (the newest unless the learner picks another)
 *   data-tutor="status"   page messages: loading, signed out, read-only, connection lost
 *
 * LESSON FRAGMENT (lessons/<nn>.html) - one section per question, id = the question id:
 *   <section id="Q1"><p><b>Q1.</b> ...prompt...</p></section>     (R1 for reviews, G for the guess)
 *   tutor.js labels each section "Lesson <nn>, <id>" (aria-label) and marks it data-comment-target, so a
 *   comment anywhere in it anchors to the section and its location names the lesson and question.
 *   It adds to each section a <div class="tutor-q"> holding, in order:
 *     .tutor-attempt > .answer + blockquote.feedback   one per feedback entry
 *     .hint                                            one per entry in hints
 *     .solution                                        the question's solution; with none, after a Show me an
 *                                                      older page asked for and the tutor handled, the last hint
 *     .tutor-controls                                  .tutor-options > button.tutor-option[aria-pressed], or .tutor-input
 *     .tutor-q-actions                                 .tutor-note, for an answer that did not save
 *   After the fragment: p.pass (when the lesson passed), .tutor-actions (Done, .tutor-note) and ul.tutor-tips,
 *   which tells the learner to ask for help with a comment sent to Claude.
 *   Done's .tutor-note, while a Claude session has claimed the request and not handled it, holds span.tutor-wait,
 *   three animated dots. A request nobody claimed within CLAIM_WAIT, or claimed longer than CLAIM_LIMIT ago,
 *   gets a note to run /tutor instead.
 *   Math: $...$ and $$...$$, rendered as MathML by KaTeX, so the page needs no KaTeX stylesheet.
 *   lessons/<nn>.script runs once per render of the fragment, with `root` = the lesson's container.
 *
 * DATA - reads goal/main, lessons, lessons/<nn>/questions, answers and requests of the lesson shown.
 *   Writes only answers/<nn>-<id> (set: lesson, question, type, answer, attempt, savedAt, recorded: false)
 *   and requests/<nn>-<base36 ms> (kind: "done", lesson, question: null, at, sent, threadId, claimedAt: null,
 *   claimedBy: null, handled: false, handledAt). Pages before VERSION 6 also wrote the kinds hint, showme, easy
 *   and hard. The tutor sets claimedAt and claimedBy (its session) when it starts on a request, and handled
 *   when it is done.
 *   Never goal or lessons: rules do not limit the owner, and the learner is the owner.
 *
 * LOCKS - from documents only, so two open devices agree:
 *   closed  the lesson has pass, or the answer is recorded and the question has no redo
 *   locked  closed, or an unhandled done request for the lesson exists, or the viewer cannot write
 *   attempt the answer's attempt; one higher once a recorded answer gets redo
 */
(() => {
  "use strict";

  const VERSION = 7;
  const KATEX = "https://cdn.jsdelivr.net/npm/katex@0.19.0/dist/";
  const KATEX_JS = ["katex.min.js", "sha384-QFFtAGzvvj+bfgCGxXJlNZZR1nXEZgvG8tDLCCY1F19xl20WlfTYgguB4VcNdxYk"];
  const SAVE_DELAY = 600;
  const NOTHING_NEW = "Answer a question first, then press Done.";
  const CLAIM_WAIT = 30e3;      // a watching session claims a sent request within this, or the note says to run /tutor
  const CLAIM_LIMIT = 10 * 60e3; // a claim older than this is taken as a session that stopped

  const S = {
    db: null, comments: null, readOnly: false, failed: null,
    goal: null, lessons: new Map(), current: null, shown: null,
    questions: new Map(), answers: new Map(), requests: [],
    lessonUnsubs: [], savers: new Map(), busy: false, notes: {},
    recheckAt: Infinity, recheck: null,
  };

  const slot = name => document.querySelector(`[data-tutor="${name}"]`);
  const el = (tag, attrs, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") n.className = v;
      else if (k === "html") n.innerHTML = v;
      else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
      else n.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids) if (kid != null) n.append(kid);
    return n;
  };
  // Rebuild a node's content only when its key changes, so live snapshots do not reset it.
  const keyed = (node, key, build) => {
    if (!node || node.__tutorKey === key) return false;
    node.__tutorKey = key;
    node.replaceChildren();
    build(node);
    return true;
  };
  const byId = (a, b) => a.localeCompare(b, undefined, { numeric: true });
  const now = () => new Date().toISOString();
  const clock = iso => new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  const errCode = e => (e && e.code) || "error";
  const letter = i => String.fromCharCode(97 + i);

  // ---------- default look: zero specificity, so the page's own CSS wins ----------

  document.head.append(el("style", {}, `
:where(.tutor-q){display:grid;gap:.6rem;margin-top:.75rem}
:where(.tutor-q > :empty){display:none}
:where(.tutor-options){display:grid;gap:.4rem}
:where(.tutor-option){display:flex;gap:.5rem;text-align:left;padding:.5rem .75rem;border:1px solid;border-radius:8px;background:none;color:inherit;font:inherit;cursor:pointer}
:where(.tutor-option[aria-pressed="true"]){outline:2px solid;outline-offset:-1px}
:where(.tutor-input){box-sizing:border-box;width:100%;padding:.5rem;border:1px solid;border-radius:8px;background:none;color:inherit;font:inherit}
:where(textarea.tutor-input){min-height:4.5em;field-sizing:content}
:where(.tutor-option:disabled,.tutor-input:disabled,.tutor-actions button:disabled){opacity:.6;cursor:default}
:where(.tutor-q-actions,.tutor-actions){display:flex;flex-wrap:wrap;gap:.5rem;align-items:center}
:where(.tutor-actions){margin-top:1.25rem}
:where(.tutor-note){font-size:.85em;opacity:.8}
:where(.tutor-tips){margin:1rem 0 0;padding-left:1.2em;font-size:.9em;opacity:.8}
:where(.tutor-wait){display:inline-flex;gap:.3em;padding:.3em 0;vertical-align:middle}
:where(.tutor-wait i){width:.5em;height:.5em;border-radius:50%;background:currentColor;animation:tutor-wait 1.2s ease-in-out infinite}
:where(.tutor-wait i:nth-child(2)){animation-delay:.15s}
:where(.tutor-wait i:nth-child(3)){animation-delay:.3s}
@keyframes tutor-wait{0%,80%,100%{opacity:.25;transform:scale(.75)}40%{opacity:1;transform:none}}
@keyframes tutor-wait-still{0%,80%,100%{opacity:.25}40%{opacity:1}}
@media (prefers-reduced-motion:reduce){:where(.tutor-wait i){animation-name:tutor-wait-still;animation-duration:2.4s}}
:where(.tutor-q .answer){white-space:pre-wrap}
:where(.solution)::before{content:"Answer";display:block;font-weight:600}
:where(.tutor-plan button){font:inherit;color:inherit;background:none;border:0;padding:0;text-decoration:underline;cursor:pointer}
`));

  // ---------- math ----------

  // TeX sits in one text node: $...$ inline, $$...$$ display. Code, scripts and the learner's answers are skipped.
  const MATH = /\$\$([\s\S]+?)\$\$|\$([^$]+?)\$/g;
  const SKIP = "script, style, textarea, pre, code, option, .tutor-raw";
  let katexReady = null;
  function typeset(node) {
    if (!node || !node.textContent.includes("$")) return;
    katexReady = katexReady || new Promise((ok, fail) => {
      document.head.append(el("script", { src: KATEX + KATEX_JS[0], integrity: KATEX_JS[1], crossorigin: "anonymous", onload: ok, onerror: fail }));
    }).catch(() => null);
    katexReady.then(() => {
      if (!window.katex || !node.isConnected) return;
      const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
      const found = [];
      while (walker.nextNode()) {
        const t = walker.currentNode;
        if (t.data.includes("$") && !t.parentElement.closest(SKIP)) found.push(t);
      }
      for (const t of found) {
        const html = t.data.replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c])
          .replace(MATH, (m, display, inline) => window.katex.renderToString(
            (display || inline).replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&"),
            { displayMode: !!display, output: "mathml", throwOnError: false }));
        const tpl = document.createElement("template");
        tpl.innerHTML = html;
        t.replaceWith(tpl.content);
      }
    });
  }

  // ---------- start ----------

  const use = name => (window.claude && window.claude.use ? window.claude.use(name) : Promise.resolve(null)).catch(() => null);

  function start() {
    document.documentElement.dataset.tutorJs = VERSION;
    renderStatus();
    use("comments").then(c => { S.comments = c; });
    use("user").then(async u => {
      const can = u && u.can ? await Promise.resolve(u.can("data.write")).catch(() => null) : null;
      if (can === false) { S.readOnly = true; schedule(); }
    });
    use("db").then(db => {
      S.db = db;
      if (!db) { S.failed = "nodb"; renderStatus(); return; }
      db.doc("goal/main").onSnapshot(snap => { S.goal = snap.exists ? snap.data() : null; S.loaded = true; schedule(); }, lost);
      db.collection("lessons").onSnapshot(snap => {
        S.lessons = new Map(snap.docs.map(d => [d.id, d.data()]));
        const ids = [...S.lessons.keys()].sort(byId);
        const newest = ids[ids.length - 1] || null;
        if (S.shown === null || S.shown === S.current || !S.lessons.has(S.shown)) showLesson(newest);
        S.current = newest;
        schedule();
      }, lost);
    });
  }

  function lost(e) {
    if (e && e.code === "revoked") S.readOnly = true;
    S.failed = "lost";
    schedule();
  }

  function showLesson(id) {
    if (id === S.shown) return;
    S.lessonUnsubs.forEach(u => u());
    S.lessonUnsubs = [];
    S.savers.forEach(s => s.flush().catch(() => {}));
    S.savers.clear();
    S.questions = new Map(); S.answers = new Map(); S.requests = [];
    S.notes = {};
    S.shown = id;
    const box = slot("lesson");
    if (box) box.__tutorKey = null;
    if (!id) return schedule();
    const db = S.db;
    S.lessonUnsubs.push(
      db.collection(`lessons/${id}/questions`).onSnapshot(snap => {
        S.questions = new Map(snap.docs.map(d => [d.id, d.data()])); schedule();
      }, lost),
      db.collection("answers").where("lesson", "==", id).onSnapshot(snap => {
        S.answers = new Map(snap.docs.map(d => [d.data().question, d.data()])); schedule();
      }, lost),
      db.collection("requests").where("lesson", "==", id).onSnapshot(snap => {
        S.requests = snap.docs.map(d => ({ id: d.id, ...d.data() })).sort((a, b) => byId(a.id, b.id)); schedule();
      }, lost),
    );
    schedule();
  }

  let queued = false;
  function schedule() {
    if (queued) return;
    queued = true;
    // Not requestAnimationFrame: it never fires in a hidden tab or frame.
    setTimeout(() => { queued = false; render(); }, 0);
  }

  function render() {
    renderStatus();
    const g = S.goal || {};
    const t = slot("title"); if (t && g.title && t.textContent !== g.title) t.textContent = g.title;
    const gl = slot("goal"); if (gl && g.goal && gl.textContent !== g.goal) gl.textContent = g.goal;
    renderPlan();
    renderReviews();
    S.recheckAt = Infinity;
    renderLesson();
    // A request note changes with time alone, with no snapshot to trigger a render.
    clearTimeout(S.recheck);
    // Capped, since a claimedAt from a wrong clock can lie far ahead, past what setTimeout can wait.
    if (S.recheckAt < Infinity) S.recheck = setTimeout(schedule, Math.min(CLAIM_LIMIT, Math.max(0, S.recheckAt - Date.now())) + 50);
  }

  function renderStatus() {
    const s = slot("status");
    if (!s) return;
    const msg = S.failed === "nodb" ? "Open this page in Claude while signed in to see your lessons."
      : S.failed === "lost" ? "The live connection stopped. Reload the page."
      : !S.db ? "Loading..."
      : S.readOnly ? "You can read this goal but not answer."
      : S.loaded && !S.goal && !S.current ? "This goal has no lessons yet. Ask Claude to run /tutor."
      : "";
    if (s.textContent !== msg) s.textContent = msg;
    s.hidden = !msg;
  }

  // ---------- plan and reviews ----------

  function renderPlan() {
    const box = slot("plan");
    const plan = (S.goal && S.goal.plan) || [];
    const ids = [...S.lessons.keys()].sort(byId);
    const extra = ids.filter(id => !plan.some(p => p.id === id))
      .map(id => ({ id, title: S.lessons.get(id).title || id, status: "" }));
    const items = plan.concat(extra).sort((a, b) => byId(a.id, b.id));
    keyed(box, JSON.stringify([items, ids, S.shown]), node => {
      if (!items.length) return;
      node.append(el("ol", { class: "tutor-plan" }, ...items.map(p => {
        const label = `${p.id} ${p.title}`;
        const word = (p.status || "").split(/[ ,]/)[0];
        return el("li", { class: "tutor-plan-item", "data-status": word || "waiting", "aria-current": p.id === S.shown ? "page" : null },
          S.lessons.has(p.id) ? el("button", { type: "button", onclick: () => { showLesson(p.id); } }, label) : el("span", {}, label),
          p.status ? el("span", { class: "tutor-plan-status" }, ` - ${p.status}`) : null);
      })));
    });
  }

  function renderReviews() {
    const box = slot("reviews");
    const today = new Date().toLocaleDateString("en-CA");
    const rules = ((S.goal && S.goal.rules) || [])
      .filter(r => r.next && /^\d{4}-\d\d-\d\d$/.test(r.next))
      .sort((a, b) => a.next.localeCompare(b.next));
    keyed(box, JSON.stringify([rules, today]), node => {
      if (!rules.length) { node.append(el("p", { class: "tutor-note" }, "No reviews yet.")); return; }
      node.append(el("ul", { class: "tutor-reviews" }, ...rules.map(r => {
        const [y, m, d] = r.next.split("-").map(Number);
        const when = r.next <= today ? "due" : new Date(y, m - 1, d).toLocaleDateString([], { month: "short", day: "numeric" });
        return el("li", { "data-due": r.next <= today || null },
          el("time", { class: "tutor-review-date", datetime: r.next }, when), " ", el("span", { html: r.text || r.id }));
      })));
      typeset(node);
    });
  }

  // ---------- lesson ----------

  function renderLesson() {
    const box = slot("lesson");
    if (!box) return;
    const id = S.shown;
    const lesson = id && S.lessons.get(id);
    if (!lesson) {
      keyed(box, "none", node => { if (S.db && S.loaded) node.append(el("p", { class: "tutor-note" }, "No lesson yet.")); });
      return;
    }
    keyed(box, JSON.stringify([id, lesson.html, lesson.script]), node => {
      const body = el("div", { class: "tutor-lesson", "data-lesson": id, "data-kind": lesson.kind || "lesson", html: lesson.html || "" });
      const pass = el("p", { class: "pass", hidden: true });
      const actions = el("div", { class: "tutor-actions" },
        el("button", { type: "button", "data-kind": "done", class: "tutor-done", onclick: e => done(e.currentTarget) }, "Done"),
        el("p", { class: "tutor-note", role: "status" }));
      const tips = el("ul", { class: "tutor-tips" },
        el("li", {}, "Stuck on a question? Comment on it and send it to Claude, for a hint or the answer."),
        el("li", {}, "Too easy or too hard? Say so in a comment sent to Claude."),
        el("li", {}, "On a phone, turn on Send to Claude before you post."));
      node.append(body, pass, actions, tips);
      typeset(body);
      if (lesson.script) runScript(lesson.script, body);
    });
    const body = box.querySelector(".tutor-lesson");
    const pendingDone = S.requests.filter(r => r.kind === "done" && !r.handled).pop();

    const pass = box.querySelector(".pass");
    const passText = lesson.pass ? (typeof lesson.pass === "string" ? lesson.pass : "Passed.") : "";
    if (pass.__tutorKey !== passText) { pass.__tutorKey = passText; pass.innerHTML = passText; pass.hidden = !passText; typeset(pass); }

    const ids = [...S.questions.keys()].sort(byId);
    for (const qid of ids) renderQuestion(body, qid, S.questions.get(qid), S.answers.get(qid), lesson, pendingDone);

    const actions = box.querySelector(".tutor-actions");
    const open = ids.some(qid => !questionState(S.questions.get(qid), S.answers.get(qid), lesson).closed);
    actions.hidden = !!lesson.pass || S.readOnly || !open && !pendingDone;
    actions.querySelectorAll("button").forEach(b => { b.disabled = S.busy || !!pendingDone; });
    box.querySelector(".tutor-tips").hidden = S.readOnly;
    const st = !S.notes.lesson && pendingDone ? requestNote(pendingDone, "Done", "grading", "Grading usually takes a minute or two.") : { msg: S.notes.lesson || "" };
    setNote(actions.querySelector(".tutor-note"), st.msg, st.waiting);
  }

  // What an unhandled request's note says. The claim is checked before sent, since the page's
  // sent write can lose to the tutor's claim. Notes that change with time set when to render again.
  function requestNote(r, what, doing, takes) {
    const t = s => Date.parse(s) || 0;
    const later = at => { S.recheckAt = Math.min(S.recheckAt, at); };
    const run = "If no Claude session is open, ask Claude to run /tutor.";
    if (r.claimedAt && Date.now() < t(r.claimedAt) + CLAIM_LIMIT) {
      later(t(r.claimedAt) + CLAIM_LIMIT);
      return { msg: `Claude is ${doing}`, waiting: true };
    }
    if (r.claimedAt) return { msg: `Claude started on this at ${clock(r.claimedAt)} but has not finished. ${run}` };
    if (!r.sent) return { msg: `${what} saved at ${clock(r.at)}. No Claude session got it, so ask Claude to run /tutor.` };
    if (Date.now() < t(r.at) + CLAIM_WAIT) {
      later(t(r.at) + CLAIM_WAIT);
      return { msg: `${what} sent to Claude. ${takes}` };
    }
    return { msg: `${what} saved at ${clock(r.at)}. No Claude session has taken it yet. If none is open, ask Claude to run /tutor.` };
  }

  // A claimed request not yet handled shows animated dots, labelled for screen readers; anything else is text.
  function setNote(note, msg, waiting) {
    keyed(note, `${waiting ? "wait" : "text"}:${msg}`, node => {
      if (waiting) node.append(el("span", { class: "tutor-wait", role: "img", "aria-label": msg }, el("i"), el("i"), el("i")));
      else node.textContent = msg;
    });
  }

  function runScript(code, root) {
    const key = `__tutorRoot${Date.now().toString(36)}`;
    window[key] = root;
    root.append(el("script", {}, `(function (root) { try {\n${code}\n} catch (e) { console.error("tutor lesson script:", e); } })(window.${key});`));
    delete window[key];
  }

  function questionState(q, a, lesson) {
    const recorded = !!(a && a.recorded);
    const closed = !!lesson.pass || (recorded && !q.redo);
    const attempt = !a ? 1 : recorded ? a.attempt + 1 : a.attempt;
    const draft = a && !recorded ? a.answer : null;
    return { closed, attempt, draft };
  }

  function renderQuestion(body, qid, q, a, lesson, pendingDone) {
    let section = body.querySelector(`section#${CSS.escape(qid)}`);
    if (!section) { section = el("section", { id: qid }); body.append(section); }
    if (!section.hasAttribute("data-comment-target")) {
      section.setAttribute("aria-label", `Lesson ${S.shown}, ${qid}`);
      section.setAttribute("data-comment-target", "");
    }
    let box = section.querySelector(":scope > .tutor-q");
    if (!box) {
      box = el("div", { class: "tutor-q" },
        el("div", { class: "tutor-history" }), el("div", { class: "tutor-hints" }),
        el("div", { class: "tutor-controls" }), el("div", { class: "tutor-q-actions" }));
      section.append(box);
    }
    const st = questionState(q, a, lesson);
    const locked = st.closed || !!pendingDone || S.readOnly || S.busy;
    const options = Array.isArray(q.options) ? q.options : [];

    // Graded attempts: the answer the tutor graded, then its feedback.
    const feedback = (Array.isArray(q.feedback) ? q.feedback : []).slice().sort((x, y) => (x.attempt || 0) - (y.attempt || 0));
    const shownAnswer = (att, given) => given != null ? given : a && a.attempt === att && a.recorded ? a.answer : null;
    const history = feedback.map(f => ({ answer: shownAnswer(f.attempt, f.answer), text: f.text }));
    if (a && a.recorded && !feedback.some(f => f.attempt === a.attempt)) history.push({ answer: a.answer, text: null });
    keyed(box.querySelector(".tutor-history"), JSON.stringify([history, options]), node => {
      for (const h of history) {
        node.append(el("div", { class: "tutor-attempt" },
          h.answer != null ? answerView(q.type, h.answer, options) : null,
          h.text ? el("blockquote", { class: "feedback", html: h.text }) : null));
      }
      typeset(node);
    });

    // An older tutor may have written a Show me answer into hints: then the last hint is the answer.
    const allHints = Array.isArray(q.hints) ? q.hints : [];
    const fallback = !q.solution && allHints.length > 0 && S.requests.some(r => r.question === qid && r.kind === "showme" && r.handled);
    const hints = fallback ? allHints.slice(0, -1) : allHints;
    const solution = q.solution || (fallback ? allHints[allHints.length - 1] : null);
    keyed(box.querySelector(".tutor-hints"), JSON.stringify([hints, solution]), node => {
      hints.forEach(h => node.append(el("div", { class: "hint", html: h })));
      if (solution) node.append(el("div", { class: "solution", html: solution }));
      typeset(node);
    });

    const controls = box.querySelector(".tutor-controls");
    if (st.closed) keyed(controls, "closed", () => {});
    else if (keyed(controls, JSON.stringify([q.type, options, st.attempt]), node => buildControls(node, qid, q, options))) {
      fillControls(controls, q.type, st.draft, null);
    } else fillControls(controls, q.type, st.draft, a);
    controls.querySelectorAll("button, input, textarea").forEach(c => { c.disabled = locked; });
    const saver = S.savers.get(qid);
    if (saver && saver.attempt !== st.attempt) { saver.attempt = st.attempt; saver.last = undefined; }

    const acts = box.querySelector(".tutor-q-actions");
    keyed(acts, String(st.closed || S.readOnly), node => {
      if (!st.closed && !S.readOnly) node.append(el("span", { class: "tutor-note", role: "status" }));
    });
    const note = acts.querySelector(".tutor-note");
    if (note) setNote(note, S.notes[qid] || "", false);
  }

  function answerView(type, answer, options) {
    if (!String(answer).trim()) return el("div", { class: "answer tutor-blank" }, "Left blank");
    if (type === "mc" && /^[a-z]$/.test(answer)) {
      const i = answer.charCodeAt(0) - 97;
      return el("div", { class: "answer" }, el("b", {}, `${answer}) `), el("span", { html: options[i] || "" }));
    }
    return el("div", { class: "answer tutor-raw" }, String(answer));
  }

  function buildControls(node, qid, q, options) {
    const saver = saverFor(qid, q.type);
    if (q.type === "mc") {
      const group = el("div", { class: "tutor-options", role: "group", "aria-label": `Answer to ${qid}` });
      options.forEach((opt, i) => group.append(el("button", {
        type: "button", class: "tutor-option", "data-value": letter(i), "aria-pressed": "false",
        onclick: e => {
          group.querySelectorAll(".tutor-option").forEach(b => b.setAttribute("aria-pressed", String(b === e.currentTarget)));
          saver.queue(letter(i), 0);
        },
      }, el("b", {}, `${letter(i)})`), el("span", { html: opt }))));
      node.append(group);
      typeset(group);
      return;
    }
    const attrs = { class: "tutor-input", "aria-label": `Answer to ${qid}`, autocomplete: "off", autocapitalize: "off", spellcheck: "false",
      oninput: e => saver.queue(e.target.value, SAVE_DELAY), onblur: () => saver.flush() };
    node.append(q.type === "number" ? el("input", { type: "text", ...attrs }) : el("textarea", { rows: 3, ...attrs }));
  }

  // Show the saved answer, unless the learner is editing here, a save is on its way,
  // or the snapshot is older than this page's last save. `a` is null right after a rebuild.
  function fillControls(node, type, draft, a) {
    const saver = S.savers.get(node.closest("section").id);
    if (a !== null && (node.contains(document.activeElement) || (saver && (saver.busy()
      || saver.wrote && (!a || a.savedAt < saver.wrote.savedAt))))) return;
    if (type === "mc") {
      node.querySelectorAll(".tutor-option").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.value === draft)));
    } else {
      const input = node.querySelector(".tutor-input");
      if (input && input.value !== (draft || "")) input.value = draft || "";
    }
  }

  // ---------- saving answers ----------

  function saverFor(qid, type) {
    let s = S.savers.get(qid);
    if (s && s.type === type) return s;
    const lesson = S.shown;
    let timer = null, pending = null, chain = Promise.resolve(), inflight = 0;
    s = {
      type, attempt: 1, last: undefined, wrote: null,
      busy: () => pending !== null || inflight > 0,
      queue(value, delay) {
        pending = value;
        clearTimeout(timer);
        timer = setTimeout(() => s.flush(), delay);
      },
      flush() {
        clearTimeout(timer);
        if (pending === null) return chain;
        const value = pending, attempt = s.attempt, savedAt = now();
        pending = null;
        if (value === s.last) return chain;
        inflight++;
        // A failed write must not block the ones after it.
        chain = chain.catch(() => {}).then(() => S.db.doc(`answers/${lesson}-${qid}`).set({
          lesson, question: qid, type, answer: value, attempt, savedAt, recorded: false,
        })).then(() => {
          s.last = value; s.wrote = { value, savedAt }; note(qid, "");
          if (S.notes.lesson === NOTHING_NEW) note("lesson", "");
        }, e => {
          if (errCode(e) === "invalid_argument") S.readOnly = true;
          note(qid, `Not saved (${errCode(e)}).`);
          throw e;
        }).finally(() => { inflight--; });
        return chain;
      },
    };
    S.savers.set(qid, s);
    return s;
  }

  function note(key, msg) { S.notes[key] = msg; schedule(); }

  // ---------- Done ----------

  async function canSend() {
    if (!S.comments) return "off";
    try { return await S.comments.canSendToClaude(); } catch (e) { return "off"; }
  }

  function claudeText(lesson, id) {
    return `Done with lesson ${lesson}. Use the tutor skill (/tutor) on this goal: the request is requests/${id},`
      + ` and the answers are answers/${lesson}-*.`
      // Read by whatever session gets it, so the checks are spelled out in full: old sessions lack the skill's own,
      // and Claude Code's automatic comment reply, which often answers first, runs without the skill at all.
      + ` If you cannot use the tutor skill here, write nothing to this goal and leave the request unclaimed. Reply only:`
      + ` "Saved. If a Claude Code session is watching this page, it grades this in a minute or two. If not, ask Claude to run /tutor."`
      + ` If you can, check it first: this page needs tutor.js VERSION ${VERSION} or higher, from the VERSION line in the`
      + ` tutor.js file in the tutor skill's folder. A skill with no tutor.js file (tutor 2.x) or with a lower VERSION is older:`
      + ` write nothing to this goal and leave the request unclaimed. In Claude Code, stop watching this page. Then reply only,`
      + ` with acknowledge_duplicate: true if a Claude reply is already in the thread:`
      + ` "This session's tutor is older than the page. Update the tutor plugin, then run /tutor in a new Claude Code session."`;
  }

  // Save the request first, so it is there with or without a watching session; then send.
  async function done(button) {
    if (S.busy || !S.db || S.readOnly) return;
    const lesson = S.shown;
    S.busy = true;
    note("lesson", "Saving...");
    try {
      const anchor = S.comments ? await S.comments.anchorFor(button).catch(() => null) : null;
      const can = canSend();
      const results = await Promise.allSettled([...S.savers.values()].map(s => s.flush()));
      if (results.some(r => r.status === "rejected")) { note("lesson", "An answer did not save. Try Done again."); return; }
      if (!hasNewAnswer(S.lessons.get(lesson) || {})) { note("lesson", NOTHING_NEW); return; }
      const id = `${lesson}-${Date.now().toString(36)}`;
      const ref = S.db.doc(`requests/${id}`);
      const at = now();
      try {
        await ref.set({ kind: "done", lesson, question: null, at, sent: false, threadId: null, claimedAt: null, claimedBy: null, handled: false, handledAt: null });
      } catch (e) {
        note("lesson", `Not saved (${errCode(e)}). Try again.`);
        return;
      }
      if (anchor && await can === "available") {
        note("lesson", "Sending to Claude...");
        try {
          const r = await S.comments.sendToClaude({ anchor, text: claudeText(lesson, id) });
          await ref.update({ sent: true, threadId: r.threadId }).catch(() => {});
        } catch (e) { /* claude_unavailable and the rest: the saved request still stands */ }
      }
      // Done then shows its state from the request document.
      note("lesson", "");
    } finally {
      S.busy = false;
      schedule();
    }
  }

  // Done needs something to grade: an open question with an answer saved since its last grading.
  // The page's own last write counts too, in case its snapshot has not arrived yet.
  function hasNewAnswer(lesson) {
    return [...S.questions].some(([qid, q]) => {
      const a = S.answers.get(qid);
      if (questionState(q, a, lesson).closed) return false;
      if (a && !a.recorded && String(a.answer).trim()) return true;
      const w = S.savers.has(qid) && S.savers.get(qid).wrote;
      return !!w && String(w.value).trim() !== "" && (!a || w.savedAt > a.savedAt);
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
