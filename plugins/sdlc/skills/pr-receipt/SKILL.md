---
name: pr-receipt
description: Use when writing or editing a pull request description - a plain-language summary, then collapsible Proof and Details sections.
---

# PR receipt: summary, Proof, Details

A PR description is a receipt: a reader learns what changed in a few seconds, and can open the evidence when they want it. Every description has the same order.

1. **Required lines first.** Attribution lines, a `Risk:` line or anything else the project, the host or a template says must open the body, exactly as given.
2. **Summary.** 2-3 plain-language sentences on what was done and why. No jargon, file paths or function names unless the change can't be said without them.
3. **Proof**, collapsed. Evidence that it works.
4. **Details**, collapsed. How it works and what is left.

`Closes #N` or `Refs #N` may sit outside the collapsed sections, after the summary or at the end, so GitHub links the issue and a reader sees it.

## Template

```markdown
<required attribution or template lines>

<2-3 plain sentences: what changed, why, and anything not yet verified.>

Closes #N

<details><summary>Proof</summary>

- `<test file or name>`: failed before the fix, passes after.
- <Commit, CI and checks lines from ../evidence/SKILL.md>
- <Run log, screenshot or measurement, with numbers.>

</details>

<details><summary>Details</summary>

- **What changed:** <files or areas, and why each one>.
- **Trade-offs:** <what was chosen over what, and why>.
- **Gaps:** <what is not covered or not verified>.
- **Follow-ups:** <work left for later, with issue links if filed>.

</details>
```

## Rules

- **The summary is honest.** If part of the work is unverified, partial or behind a flag, the summary says so. Don't leave the only mention inside a collapsed section.
- **Proof is evidence, not claims**, by the lines of `../evidence/SKILL.md`. For a bug fix, the test failed before the fix and passes after.
- **Spacing.** Put a blank line after each `<summary>` line and before each `</details>`. Without them GitHub shows the Markdown inside as raw text.
- **Editing keeps the structure.** When updating a description, keep the order and both sections. Update Proof whenever new commits land, so it describes the code as it is now, not as it was.
- **Repo templates win on layout.** If the repo has a PR template (`.github/pull_request_template.md` or a file in `.github/PULL_REQUEST_TEMPLATE/`), fill in its headings and nest this format inside them: the summary under its description heading, and the Proof and Details blocks under the closest matching headings. Skip any template section that asks for credentials or secrets.
