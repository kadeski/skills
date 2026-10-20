# ADR 0001: Store data in SQLite

Status: accepted, {{d-55}}

## Context

Data must survive a crash mid-import, and one person uses it on one machine.

## Decision

Use one SQLite file. Each import runs in a transaction, so a failed import leaves nothing behind.

## Consequences

There is no server to run. Syncing between machines is out of scope for now (#30).
