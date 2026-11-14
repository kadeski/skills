# tutor.js demo

A plain goal page around `plugins/tutor/skills/tutor/tutor.js`, and one sample goal to load into it. Use it to test `tutor.js` by hand on desktop and phone. It does not ship.

- `index.html` - the page: slots for title, goal, status, plan, reviews and lesson, plus its own look.
- `seed.json` - the sample goal as `ArtifactData` `batch` writes: `goal/main`, three lessons (01 and 02 passed, 03 open with a review, a redo, a hint, a lesson script and math), answers and handled requests, one of them a Hint request from a page before `tutor.js` 6, kept to check old data still shows.

## Publish and seed

1. Publish `index.html` with the Artifact tool: `files: {"tutor.js": "plugins/tutor/skills/tutor/tutor.js"}` and `capabilities: {db: {rules: [{path: "goal", write: "owner"}, {path: "lessons", write: "owner"}]}, comments: {}}`.
2. Seed it after the publish: one `ArtifactData` `batch` with the entries of `seed.json`.
3. To test Done with a session watching, keep the publishing session open; to test without one, close every Claude session first.

To update `tutor.js` on the published demo from another session, read the artifact, read its `index.html` with `path`, list its files, then publish that saved file to the same URL with the new `tutor.js` in `files` and no `capabilities`, which keeps the old ones. Then set `goal/main.tutorJs` to the new `VERSION`. `seed.json` sets it too, so bump it there with every `VERSION`.

To reset, delete the `answers` and `requests` documents the page wrote, then run the seed again.
