# Study - platform checks

Results of the spec section 12 checks, run headless on Claude Code 2.1.310 on 2026-10-25 with a scratch plugin loaded by `--plugin-dir`. `contracts.md` already follows the decisions below.

| Check | Result | Decision |
|---|---|---|
| Hooks in a skill's frontmatter register, with `${CLAUDE_PLUGIN_ROOT}` expanded and `CLAUDE_PLUGIN_OPTION_DATA_DIR` set | Partly. They register and the root expands, but the option env var is never set in skill hooks, they last only for the process that ran the skill (gone after `--resume`), and a skill's `SessionStart` `compact` hook never fired | Fallback: plugin-wide `hooks/hooks.json`. The `active` marker keeps other sessions out. Skills declare no `hooks:` |
| The hook learns the data folder | `hooks.json` hooks get `CLAUDE_PLUGIN_OPTION_DATA_DIR` once the learner has saved a value; with only the default, it is missing | The hook uses `store.resolve_data_dir()`: the env var, else `~/Study`, which is the default |
| A `directory` `userConfig` default of `~/Study` reaches the server | Yes, as the literal `~/Study`: `~` is never expanded, for the default or a saved value. The MCP server's env has no `CLAUDE_PLUGIN_OPTION_*` | The server takes `--data-dir` and expands `~` (`store.resolve_data_dir`). `validate --strict` accepts `"type": "directory"` |
| `additionalContext` reaches the model | PostToolUse: yes. UserPromptSubmit: yes. SessionStart `compact`: yes from `hooks.json` | Primary design holds |
| `${CLAUDE_SESSION_ID}` in a skill equals `session_id` in hook input | Yes, the same UUID | Primary design holds |
| A plugin subagent in the background can call the plugin's MCP tools | Yes, through the same server process | The extractor calls `graph_merge` itself |
| One allow rule `mcp__plugin_study_study` covers every tool | Yes | README tells the learner to allow it once |
| PostToolUse input for AskUserQuestion | Through an SDK host: `tool_input` is `{questions: [{question, header, options: [{label, description}], multiSelect}], answers: {"<question text>": "<label>"}}` and `tool_response` is the same object | Matches `contracts.md` section 6. The hand check below settles notes, multi-select and "Other" |
| Answer notes exist in both the terminal and the desktop app | None found in either (hand check below) | Fallback, asked only when needed: after the verdict the teacher asks for the learner's thinking in chat on a wrong answer whose cause it can't tell, or a right answer it doubts. The hook still logs notes if an app sends them |

Other findings:

- UserPromptSubmit also fires for prompts the learner didn't type: a background agent's `<task-notification>` arrives as a prompt. The hook must not log those as the learner's words or link them to a free-text question (`contracts.md` section 6).
- Under `--plugin-dir` the plugin id is `study@inline`; tool names stay `mcp__plugin_study_study__<tool>`.
- Claude Code 2.1.310 first sends `server/discover` (the newest MCP spec has no `initialize`), gets `-32601` from our server, then falls back to `initialize` at `2025-11-25`. The server keeps the `initialize` handshake.
- Placeholders such as `${CLAUDE_SESSION_ID}` and `${CLAUDE_PLUGIN_ROOT}` are filled in only in `SKILL.md`, not in files a skill reads later, so each `SKILL.md` states both values once.

## Hand check

Run by a person on 2026-11-01, in the desktop app's Code tab and in the terminal (Claude Code 2.1.314), with a temporary PostToolUse hook logging the raw AskUserQuestion input. One call asked for a note on a picked option, two picks on a multi-select question, and an "Other" answer.

- **Notes:** the person found no way to add a note beside a picked option in either app. The only free text they found is "Other", and typing there replaces the pick. The terminal sends `"annotations": {}`, so it may have a way in that isn't shown; the desktop app sends no `annotations` key.
- **Multi-select:** the terminal sends one string joined by `", "` (`"Red, Blue"`); the desktop app sends a list (`["Red", "Blue"]`). The hook handles both: `answer_text` joins a list before parsing.
- **"Other":** the typed text is the answer string, in both apps.
- Replaying the captured inputs through `log_hook.py` graded the multi-select answer, logged the "Other" text as `other` and logged `notes` as null.
- The terminal session also returned one answer in the desktop shape (a list, no `annotations`). Where it was answered is unclear; the hook handles both shapes.
