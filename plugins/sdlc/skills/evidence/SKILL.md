---
name: evidence
description: End the final reply of a Projects thread or unattended run that changed a repo with a fixed Evidence block (commit pushed, CI read back from GitHub, checks run, what was not checked), so a summary of the run passes on proof, not claims.
---

The final reply ends with this block. Fill each line from what you saw this session. One block per repo.

```
**Evidence**
- Commit: <sha> "<subject>" on <repo>@<branch>, pushed
- CI: <workflow>: <passed | failed | running | none on this repo>, <run link>
- Checks run: `<command>` -> <result>
- Not checked: <what nothing above proves>
```

- **Commit**: pushed means read back after the push (`git ls-remote`, or the commit on GitHub). No change: `none`.
- **CI**: the run for that sha, read from GitHub (`gh run list --commit <sha>`; in a thread, the GitHub MCP `actions_list`, then match `head_sha`). Running: say so with the link, and send the result later from a scheduled check-in, not a sleep loop. Never "passed" for a run you didn't see finish. A failure leads the reply.
- **Checks run**: each command on the final state, with its result. A check run before the last change goes under Not checked.
- **Not checked**: never left out; `nothing` only when true.

Anyone summarizing the run copies the block whole, not reworded.
