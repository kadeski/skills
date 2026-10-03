#!/usr/bin/env python3
"""Open a lesson page built from tutor's head.html in Chrome, Firefox and Safari
from file://, once online and once with the CDN unreachable, and assert what
KaTeX did to the DOM. The page reports back with sendBeacon to a local server.
Safari opens in the background in your own browser; close its two tabs after.

    evals/tools/math_render.py [chrome] [firefox] [safari]"""

import json
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HEAD = (REPO / "plugins/tutor/skills/tutor/head.html").read_text()
OUT = Path(tempfile.mkdtemp(prefix="math-render-"))
PORT = 8765

BODY = r"""<title>02 Fractions</title>
<h1>02 Fractions</h1>
<p>Part of <a href="goal.md">Fractions</a>. Answer in the chat.</p>
<h2>The idea</h2>
<p id="inline">Square it: $x^2 + 2x + 1$ is $(x+1)^2$.</p>
<p>A sum, shown on its own line:</p>
<p id="display">$$\sum_{k=1}^{n} k = \frac{n(n+1)}{2}$$</p>
<p id="matrix">$$\begin{pmatrix} 1 &amp; 2 \\ 3 &amp; 4 \end{pmatrix}$$</p>
<table>
<tr><th>Fraction</th><th>Decimal</th></tr>
<tr><td id="cell">$\frac{1}{2}$</td><td>0.5</td></tr>
</table>
<h2>Questions</h2>
<section id="Q1">
<p><b>Q1.</b> A pen costs <code>$5</code>. Is $a &lt; b$ when $a = 3$?</p>
<pre class="answer">$5 and $10 (sure)</pre>
<blockquote class="feedback">You wrote <code>$5 and $10</code>. Right: $a_n$ grows (notes 2).</blockquote>
</section>
"""

PROBE = r"""<script>
addEventListener("load", () => setTimeout(async () => {
  await document.fonts.ready;
  const q = s => document.querySelectorAll(s).length;
  const r = {
    katex: q(".katex"), display: q(".katex-display"), errors: q(".katex-error"),
    in_table: q("#cell .katex"), in_feedback: q("blockquote.feedback .katex"),
    matrix: q("#matrix .katex-display"),
    pre_raw: document.querySelector("pre.answer").textContent,
    code_raw: [...document.querySelectorAll("code")].map(c => c.textContent),
    font: document.fonts.check("16px KaTeX_Main"),
    inline_text: document.getElementById("inline").textContent.includes("$x^2"),
  };
  navigator.sendBeacon("http://127.0.0.1:%d/" + location.hash.slice(1), JSON.stringify(r));
}, 500));
</script>
""" % PORT

results = {}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        results[self.path.strip("/")] = json.loads(body)
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def log_message(self, *a):
        pass


def page(online):
    head = HEAD if online else HEAD.replace("https://cdn.jsdelivr.net", "http://127.0.0.1:1")
    path = OUT / f"lesson-{'online' if online else 'offline'}.html"
    path.write_text(head + BODY + PROBE)
    return path


CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
FIREFOX = "/Applications/Firefox.app/Contents/MacOS/firefox"


def launch(browser, url):
    if browser == "chrome":
        prof = tempfile.mkdtemp()
        return subprocess.Popen([CHROME, "--headless=new", f"--user-data-dir={prof}", "--no-first-run",
                                 "--virtual-time-budget=15000", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if browser == "firefox":
        prof = tempfile.mkdtemp()
        return subprocess.Popen([FIREFOX, "--headless", "--no-remote", "--profile", prof, url],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["open", "-g", "-a", "Safari", url])
    return None


def expect(r, online):
    if r is None:
        return ["no report within timeout"]
    raw_ok = r["pre_raw"] == "$5 and $10 (sure)" and r["code_raw"] == ["$5", "$5 and $10"]
    want = {"katex": 8, "display": 2, "errors": 0, "in_table": 1, "in_feedback": 1, "matrix": 1, "font": True,
            "inline_text": False} if online else \
        {"katex": 0, "display": 0, "errors": 0, "in_table": 0, "in_feedback": 0, "matrix": 0, "inline_text": True}
    bad = [f"{k}={r[k]!r} want {v!r}" for k, v in want.items() if r[k] != v]
    return bad + ([] if raw_ok else [f"raw text changed: {r['pre_raw']!r} {r['code_raw']!r}"])


def main():
    browsers = sys.argv[1:] or ["chrome", "firefox", "safari"]
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    failed = False
    for online in (True, False):
        path = page(online)
        for b in browsers:
            key = f"{b}-{'online' if online else 'offline'}"
            proc = launch(b, f"{path.as_uri()}#{key}")
            deadline = time.time() + 30
            while key not in results and time.time() < deadline:
                time.sleep(0.2)
            if proc:
                proc.kill()
            bad = expect(results.get(key), online)
            failed |= bool(bad)
            print(f"{'PASS' if not bad else 'FAIL'} {key:16} {json.dumps(results.get(key))}")
            for x in bad:
                print(f"     {x}")
    server.shutdown()
    sys.exit(1 if failed else 0)


main()
