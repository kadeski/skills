# Design

## Storage

Books and notes live in one SQLite file. Search uses SQLite's full-text index over titles and notes (phase 2 in the [plan](../PLAN.md#2-search)).

## Export

Exports run in the background and write to the user's downloads folder. The formats are tracked in #21 and #22.
