const pending = new Map();
let nextId = 1;

const post = (msg) => window.parent.postMessage({ jsonrpc: "2.0", ...msg }, "*");
const notify = (method, params) => post({ method, params });
const request = (method, params) =>
  new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, { resolve, reject });
    post({ id, method, params });
  });

function fail(message) {
  const p = document.createElement("p");
  p.textContent = `Could not show the lesson: ${message}`;
  document.body.replaceChildren(p);
}

function render(html) {
  const doc = new DOMParser().parseFromString(html, "text/html");
  document.title = doc.title;
  document.body.replaceChildren(...doc.body.childNodes);
  // Parsed scripts never run, so swap in fresh ones to run the lesson's control as a browser would.
  for (const old of document.body.querySelectorAll("script")) {
    const s = document.createElement("script");
    for (const a of old.attributes) s.setAttribute(a.name, a.value);
    s.textContent = old.textContent;
    old.replaceWith(s);
  }
  // head.html's onload handler holds the delimiters; if KaTeX is still loading, it runs on its own.
  if (window.renderMathInElement) document.head.querySelector("script[onload]")?.onload();
}

async function show(path) {
  try {
    const result = await request("tools/call", { name: "read_lesson", arguments: { path } });
    if (result.isError) throw new Error(result.content?.[0]?.text);
    render(result.structuredContent.html);
  } catch (e) {
    fail(e.message);
  }
}

const notifications = {
  "ui/notifications/tool-input": ({ arguments: args }) => show(args.path),
};

window.addEventListener("message", (e) => {
  const m = e.data;
  if (e.source !== window.parent || m?.jsonrpc !== "2.0") return;
  if (m.method === undefined) {
    const p = pending.get(m.id);
    pending.delete(m.id);
    if (m.error) p?.reject(new Error(m.error.message));
    else p?.resolve(m.result);
  } else if (m.id !== undefined) {
    const known = m.method === "ping" || m.method === "ui/resource-teardown";
    post(known ? { id: m.id, result: {} } : { id: m.id, error: { code: -32601, message: `method not found: ${m.method}` } });
  } else {
    notifications[m.method]?.(m.params);
  }
});

function reportSize() {
  let last = "";
  new ResizeObserver(() => {
    const rect = document.documentElement.getBoundingClientRect();
    const size = { width: Math.ceil(rect.width), height: Math.ceil(rect.height) };
    if (`${size.width}x${size.height}` === last) return;
    last = `${size.width}x${size.height}`;
    notify("ui/notifications/size-changed", size);
  }).observe(document.documentElement);
}

request("ui/initialize", {
  appInfo: { name: "tutor-lesson", version: "1.0.0" },
  appCapabilities: { availableDisplayModes: ["inline"] },
  protocolVersion: "2026-01-26",
}).then(() => {
  notify("ui/notifications/initialized", {});
  reportSize();
}, (e) => fail(e.message));
