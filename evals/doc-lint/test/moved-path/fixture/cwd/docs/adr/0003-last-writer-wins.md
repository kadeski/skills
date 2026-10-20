# ADR 0003: Last writer wins

Status: accepted, {{d-12}}

When two devices edit the same note, the edit with the later server timestamp wins and the other is kept as a conflict copy. Merging edits line by line was too much work for 1.0.
