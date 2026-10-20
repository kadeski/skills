# Design

## Importing

Each bank has a small parser in `ledger/banks/`. A parser turns one CSV row into a transaction: date, amount in cents, payee. Rows that fail to parse are listed at the end of the import, not dropped.

## Storage

All data lives in one SQLite file in the user's home folder, `~/.ledger/ledger.db` (see [ADR 0001](adr/0001-sqlite.md)). Amounts are stored as integer cents.

## Speed

On {{d-2}}, importing a 10,000-row CSV took 1.4 s on a 2023 laptop.
