---
name: graph
description: Open the learner's Study knowledge graph as a page in the browser - every idea taught so far, how the ideas follow from each other, and where each was taught. Use when the learner types /graph.
argument-hint: "[goal]"
disable-model-invocation: true
---

# Graph

Build the knowledge graph page and open it. Don't read or change any Study data yourself.

1. If the learner named a goal (`$ARGUMENTS`), call `mcp__plugin_study_study__list_goals` and take the goal whose title or goal text matches it. If none matches clearly, go on without one and say the page shows every goal.
2. Call `mcp__plugin_study_study__open_graph_page`, with `goal_id` when step 1 found a goal.
3. Tell the learner the page opened in their browser and give the `path` from the result, so they can open the file again later. The page is a snapshot: `/graph` again shows what was added since.

If the tool answers with an error, tell the learner what it says, in plain words, and stop.

On the page, each dot is an idea and each small dot is a chain of reasoning, with an arrow to the idea it gives. The learner can search, pick one goal, drag dots, and click an idea to see what it follows from, what it leads to and where it was taught.
