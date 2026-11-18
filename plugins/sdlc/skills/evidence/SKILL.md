---
name: evidence
description: End the final reply of a thread or unattended run that changed a repo with a fixed Evidence block - commit pushed, CI read back from GitHub, checks run, what was not checked.
---

The final reply ends with this block, one per repo, each line from what you saw this session.

```
**Evidence**
- Commit: <sha> "<subject>" on <repo>@<branch>, pushed
- CI: <workflow>: <passed | failed | running | none on this repo>, <run link>
- Checks run: `<command>` -> <result>
- Not checked: <what nothing above proves>
```

- **Commit**: pushed means read back (`git ls-remote`, or the commit on GitHub). No change: `none`.
- **CI**: the run for that sha, from GitHub (`gh run list --commit <sha>`; in a thread, MCP `actions_list`). Running: give the link and report the result from a later check-in. Never "passed" for a run you didn't see finish. A failure leads the reply.
- **Checks run**: each command on the final state. One run before the last change goes under Not checked.
- **Not checked**: never left out; `nothing` only when true.

Anyone summarizing the run copies the block whole, not reworded.
