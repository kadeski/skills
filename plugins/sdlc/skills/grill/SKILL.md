---
name: grill
description: "Grill the user relentlessly about a plan, decision, or idea until you both share the same understanding of it. Use whenever the user wants to stress-test their thinking, pressure-test a plan or design, poke holes in an idea, or says anything like \"grill me\", for any topic, not just software."
disable-model-invocation: true
---

Interview me one question at a time, recommending an answer each time (use AskUserQuestion, one question per call, when the answer is a choice among a few options; ask open questions inline), until no decision my plan depends on is left unasked and you're confident you know what I want, then summarize and wait for my confirmation before acting. Don't ask what the code, docs or a quick command can answer: look it up and tell me what you found, and save the questions for what only I can decide. If we were shaping a software change to build, end by offering /spec to turn the summary into a spec file.
