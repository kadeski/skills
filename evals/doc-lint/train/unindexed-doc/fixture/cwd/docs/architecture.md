# Architecture

A request comes in through `src/api/routes.py`, is checked against the target allowlist, and is sent on with retries.

## Parts

- **Routes** - `src/api/routes.py` takes the webhook and returns 202 at once.
- **Sender** - `src/send/sender.py` delivers it, retrying 3 times with backoff.

## Cache

Recent responses from slow targets are kept in memory by `src/cache/memory.py`, so a retry storm does not hit the target again.
