#!/usr/bin/env python3
"""Turn tutor 1.x markdown lessons in eval fixtures into tutor 2.0 HTML pages.

    evals/tools/md2html.py FIXTURE_DIR...

For each lesson or review file in FIXTURE_DIR/cwd/<goal>/, `git mv` it from
.md to .html and write the page in its place, then point the goal.md plan
links at .html. A lesson already moved is skipped, so it is safe to rerun.

It reads only the markdown the fixtures use: headings, paragraphs, `- `
lists, pipe tables, images, fenced code, `$` and `$$` math, inline code, bold
and links, `**Q1.**` items, `Answer:` lines, `> **Feedback:**` quotes, `Hint:`
and `You can now` lines. Display math is looked up in DISPLAY, written by hand.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HEAD = (ROOT / "plugins/tutor/skills/tutor/head.html").read_text()
LESSON = re.compile(r"(\d\d-[^/]*|review-[^/]*)\.md$")
OLD_HOW = "Add `sure` or `guess` after any answer, and say `done` when finished."
NEW_HOW = "Answer in the chat ({}), add `sure` or `guess` after any answer, and say `done` when finished."

DISPLAY = {
    r"(a^m)^n = a^{m \times n}": "(aᵐ)ⁿ = aᵐⁿ",
    r"\frac{1}{3} + \frac{1}{4} = \frac{4}{12} + \frac{3}{12} = \frac{7}{12}": "1/3 + 1/4 = 4/12 + 3/12 = 7/12",
    r"\text{interest} = P \times r \times n": "interest = P × r × n",
    r"\text{percent change} = \frac{\text{new} - \text{old}}{\text{old}} \times 100":
        "percent change = (new - old) / old × 100",
    r"a + (n - 1)d": "a + (n - 1)d",
    r"A_{\text{next}} = A \times (1 + r)": "Aₙₑₓₜ = A × (1 + r)",
    r"a^{-n} = \frac{1}{a^n}": "a⁻ⁿ = 1/aⁿ",
    r"a^m \times a^n = a^{m+n}": "aᵐ × aⁿ = aᵐ⁺ⁿ",
    r"D = \frac{50 \text{ g}}{20 \text{ cm}^3} = 2.5 \text{ g/cm}^3": "D = 50 g / 20 cm³ = 2.5 g/cm³",
    r"m = \frac{\text{rise}}{\text{run}}": "m = rise / run",
    r"m = \frac{y_2 - y_1}{x_2 - x_1}": "m = (y₂ - y₁) / (x₂ - x₁)",
    r"n = \frac{\text{last} - \text{first}}{d} + 1": "n = (last - first) / d + 1",
    r"P(\text{art given music}) = \frac{\text{both}}{\text{music}} = \frac{12}{25}":
        "P(art given music) = both / music = 12/25",
}
SUP = dict(zip("0123456789+-mn", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻ᵐⁿ"))


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")


def tex(s):
    """Inline math as Unicode: powers and the times sign."""
    out = re.sub(r"\^\{([^}]*)\}|\^(\w)", lambda m: "".join(SUP[c] for c in m[1] or m[2]), s).replace(r"\times", "×")
    if re.search(r"[\\{}^_]", out):
        raise ValueError(f"no rule for math: {s}")
    return out


def inline(s):
    held = []

    def hold(html):
        held.append(html)
        return f"\0{len(held) - 1}\0"

    s = re.sub(r"`([^`]*)`", lambda m: hold(f"<code>{esc(m[1])}</code>"), s)
    s = re.sub(r"\$([^$]+)\$", lambda m: hold(esc(tex(m[1]))), s)
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
    return re.sub(r"\0(\d+)\0", lambda m: held[int(m[1])], s)


def fence(lines, i):
    """The code of the fenced block opening at lines[i], and the line after it."""
    j = i + 1
    while not lines[j].startswith("```"):
        j += 1
    return "\n".join(lines[i + 1:j]), j + 1


def blocks(lines):
    """HTML lines for plain markdown blocks: paragraphs, lists, tables, pictures, code and math."""
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("```"):
            code, i = fence(lines, i)
            out.append(f"<pre><code>{esc(code)}</code></pre>")
        elif line == "$$":
            j = lines.index("$$", i + 1)
            out.append(f"<p>{esc(DISPLAY[' '.join(lines[i + 1:j]).strip()])}</p>")
            i = j + 1
        elif m := re.fullmatch(r"!\[([^\]]*)\]\(([^)\s]+)\)", line):
            out.append(f'<img src="{m[2]}" alt="{esc(m[1]).replace(chr(34), "&quot;")}">')
            i += 1
        elif line.startswith("- "):
            out.append("<ul>")
            while i < len(lines) and lines[i].startswith("- "):
                out.append(f"<li>{inline(lines[i][2:])}</li>")
                i += 1
            out.append("</ul>")
        elif line.startswith("|"):
            out.append("<table>")
            first = True
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    tag = "th" if first else "td"
                    out.append("<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in cells) + "</tr>")
                    first = False
                i += 1
            out.append("</table>")
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(r"```|\$\$$|!\[|- |\|", lines[i]):
                para.append(lines[i])
                i += 1
            out.append(f"<p>{inline(' '.join(para))}</p>")
    return out


def convert(md, review=False):
    """A 1.x markdown lesson as a 2.0 page: head.html, a title, then the body."""
    lines = md.rstrip("\n").split("\n")
    body, title, item, i = [], "", None, 0

    def close():
        nonlocal item
        if item:
            body.append("</section>")
            item = None

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif m := re.fullmatch(r"# (.+)", line):
            title = m[1]
            body.append(f"<h1>{inline(title)}</h1>")
            i += 1
        elif m := re.fullmatch(r"## (.+)", line):
            close()
            body += ["", f"<h2>{inline(m[1])}</h2>"]
            if m[1].startswith("Guess for next time"):
                body.append('<section id="G">')
                item = "G"
            i += 1
        elif m := re.match(r"\*\*([QR]\d+)\.\*\* (.*)", line):
            close()
            item = m[1]
            body += [f'<section id="{item}">', f"<p><b>{item}.</b> {inline(m[2])}</p>"]
            i += 1
        elif line.startswith("You can now"):
            close()
            body.append(f'<p class="pass">{inline(line)}</p>')
            i += 1
        elif line.startswith("Hint:"):
            body.append(f'<p class="hint">{inline(line[5:].strip())}</p>')
            i += 1
        elif m := re.fullmatch(r"Answer:\s*(.*)", line):
            answer, i = m[1], i + 1
            if not answer:
                j = i
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines) and lines[j].startswith("```"):
                    answer, i = fence(lines, j)
            if answer.strip():
                body.append(f'<pre class="answer">{esc(answer)}</pre>')
        elif line.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(re.sub(r"^> ?", "", lines[i]))
                i += 1
            fb = quote[0].startswith("**Feedback:**")
            if fb:
                quote[0] = quote[0][len("**Feedback:**"):].strip()
            inner = blocks(quote)
            tag = '<blockquote class="feedback">' if fb else "<blockquote>"
            if len(inner) == 1 and inner[0].startswith("<p>"):
                body.append(f"{tag}{inner[0][3:-4]}</blockquote>")
            else:
                body += [tag, *inner, "</blockquote>"]
        else:
            j = fence(lines, i)[1] if line.startswith("```") else i + 1
            while j < len(lines) and lines[j].strip() and not re.match(r"#|\*\*[QR]\d+\.\*\*|Answer:|>|You can now|Hint:|```", lines[j]):
                j += 1
            chunk = lines[i:j]
            if chunk[0].startswith("Part of [") and OLD_HOW in chunk[0]:
                chunk[0] = chunk[0].replace(OLD_HOW, NEW_HOW.format("`r1: ...`" if review else "`1: ...`, `g: c`"))
            body += blocks(chunk)
            i = j
    close()
    return f"{HEAD}<title>{esc(title)}</title>\n" + "\n".join(body) + "\n"


def convert_fixture(fixture):
    for md in sorted(fixture.glob("cwd/*/*.md")):
        if not LESSON.search(md.name):
            continue
        page = md.with_suffix(".html")
        subprocess.run(["git", "mv", str(md), str(page)], check=True, cwd=ROOT)
        page.write_text(convert(page.read_text(), review=md.name.startswith("review-")))
    for goal in fixture.glob("cwd/*/goal.md"):
        text = goal.read_text()
        goal.write_text(re.sub(r"\]\(((?:\d\d|review)-[^)]*)\.md\)", r"](\1.html)", text))


if __name__ == "__main__":
    for d in sys.argv[1:]:
        convert_fixture(Path(d).resolve())
