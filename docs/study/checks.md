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
| PostToolUse input for AskUserQuestion | Through an SDK host: `tool_input` is `{questions: [{question, header, options: [{label, description}], multiSelect}], answers: {"<question text>": "<label>"}}` and `tool_response` is the same object | Matches `contracts.md` section 6. Notes, multi-select and "Other" are still unconfirmed (below) |
| Answer notes exist in both the terminal and the desktop app | Not checked: needs a person | Below |

Other findings:

- UserPromptSubmit also fires for prompts the learner didn't type: a background agent's `<task-notification>` arrives as a prompt. The hook must not log those as the learner's words or link them to a free-text question (`contracts.md` section 6).
- Under `--plugin-dir` the plugin id is `study@inline`; tool names stay `mcp__plugin_study_study__<tool>`.

## Still to check by hand

Load the built plugin with `claude --plugin-dir plugins/study`, and in both the terminal and the desktop app answer one AskUserQuestion with a note, one multi-select question, and one "Other" answer, with the hook's raw input logged. Record:

- where the note appears (`tool_input.annotations[<question>].notes` is assumed)
- how several picked labels are joined (`", "` is assumed)
- how "Other" text appears (as the answer string itself is assumed)

If notes are missing in either app, the fallback is spec section 12's: ask for the learner's thinking in chat after the answer.
