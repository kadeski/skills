import { readFileSync, statSync } from "node:fs";
import { dirname, isAbsolute } from "node:path";
import { createInterface } from "node:readline";
import { fileURLToPath, pathToFileURL } from "node:url";

const LESSON_URI = "ui://tutor/lesson";
const UI = "io.modelcontextprotocol/ui";

const version = JSON.parse(readFileSync(new URL("../plugin.json", import.meta.url), "utf8")).version;
const shell =
  readFileSync(new URL("../skills/tutor/head.html", import.meta.url), "utf8") +
  "<title>Lesson</title>\n<script>\n" +
  readFileSync(new URL("./panel.js", import.meta.url), "utf8") +
  "</script>\n";

function selfContained(html, lessonDir) {
  const base = pathToFileURL(lessonDir + "/");
  return html.replace(/(<img\b[^>]*?\ssrc=)(["'])(.*?)\2/gi, (tag, head, q, src) => {
    if (/^([a-z][a-z0-9+.-]*:|\/)/i.test(src)) return tag;
    const file = fileURLToPath(new URL(src, base));
    if (!file.toLowerCase().endsWith(".svg")) return tag;
    try {
      return `${head}${q}data:image/svg+xml;base64,${readFileSync(file).toString("base64")}${q}`;
    } catch {
      return tag;
    }
  });
}

function lessonPath({ path } = {}) {
  if (typeof path !== "string" || !isAbsolute(path)) return { error: `path must be absolute: ${path}` };
  if (!path.endsWith(".html")) return { error: `path must be a .html lesson page: ${path}` };
  if (!statSync(path, { throwIfNoEntry: false })?.isFile()) return { error: `no file at ${path}` };
  return { path };
}

const text = (t) => [{ type: "text", text: t }];
const pathInput = {
  type: "object",
  properties: { path: { type: "string", description: "Absolute path to the lesson .html page" } },
  required: ["path"],
};

const tools = {
  show_lesson: {
    description:
      "Shows a tutor lesson page in the chat. In a tutor run, call it once for each lesson or review page graded or written, graded first, with the page's absolute path. Returns the page's file:// link; still give it in the reply.",
    inputSchema: pathInput,
    _meta: { ui: { resourceUri: LESSON_URI }, "ui/resourceUri": LESSON_URI },
    run: (path) => ({ content: text(pathToFileURL(path).href) }),
  },
  read_lesson: {
    description: "Returns a lesson page as self-contained HTML for the lesson panel.",
    inputSchema: pathInput,
    _meta: { ui: { visibility: ["app"] } },
    run: (path) => ({
      content: text(`Lesson page ${path}`),
      structuredContent: { html: selfContained(readFileSync(path, "utf8"), dirname(path)) },
    }),
  },
};

class RpcError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
  }
}

const handlers = {
  initialize: ({ protocolVersion, clientInfo, capabilities }) => {
    const ext = capabilities?.extensions?.[UI];
    process.stderr.write(
      `tutor: client ${clientInfo?.name} ${clientInfo?.version}, ${UI}: ${ext ? JSON.stringify(ext) : "absent"}\n`,
    );
    return { protocolVersion, capabilities: { tools: {}, resources: {} }, serverInfo: { name: "tutor", version } };
  },
  ping: () => ({}),
  "tools/list": () => ({
    tools: Object.entries(tools).map(([name, { run, ...def }]) => ({ name, ...def })),
  }),
  "tools/call": ({ name, arguments: args }) => {
    const tool = tools[name];
    if (!tool) throw new RpcError(-32602, `unknown tool: ${name}`);
    const { path, error } = lessonPath(args);
    return error ? { content: text(error), isError: true } : tool.run(path);
  },
  "resources/list": () => ({
    resources: [{ uri: LESSON_URI, name: "lesson", description: "Tutor lesson panel", mimeType: "text/html;profile=mcp-app" }],
  }),
  "resources/read": ({ uri }) => {
    if (uri !== LESSON_URI) throw new RpcError(-32002, `resource not found: ${uri}`);
    return {
      contents: [
        {
          uri,
          mimeType: "text/html;profile=mcp-app",
          text: shell,
          _meta: { ui: { csp: { resourceDomains: ["https://cdn.jsdelivr.net"] }, prefersBorder: true } },
        },
      ],
    };
  },
};

function reply(id, method, params) {
  const handler = Object.hasOwn(handlers, method) ? handlers[method] : null;
  if (!handler) return { jsonrpc: "2.0", id, error: { code: -32601, message: `method not found: ${method}` } };
  try {
    return { jsonrpc: "2.0", id, result: handler(params ?? {}) };
  } catch (e) {
    return { jsonrpc: "2.0", id, error: { code: e.code ?? -32603, message: e.message } };
  }
}

createInterface({ input: process.stdin })
  .on("line", (line) => {
    let msg;
    try {
      msg = JSON.parse(line);
    } catch {
      return;
    }
    if (msg?.id === undefined || msg.method === undefined) return;
    process.stdout.write(JSON.stringify(reply(msg.id, msg.method, msg.params)) + "\n");
  })
  .on("close", () => process.exit(0));
