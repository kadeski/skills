def grade(r):
    r.check("no files created", not r.new_files(), r.new_files())
    r.check("no files changed", not r.changed_files(), r.changed_files())
    lines = [x for x in r.final.strip().splitlines() if x.strip()]
    r.check("reply is one line", len(lines) == 1, r.final[:300])
    r.check("no em dash in reply", "\u2014" not in r.final)
    r.claim("ask", "The tutor's reply asks whether the learner is done or wants to answer Q3 first, and names Q3 as blank.")
    r.claim("no-grade", "The tutor's reply does not grade or comment on Q1 or Q2 and does not give the answer to Q3.")
