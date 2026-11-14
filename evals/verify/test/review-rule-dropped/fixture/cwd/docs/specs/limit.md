# Scheduled message limit

Tier: 2 · Status: building · Risk: normal

## Goal
A user can't pile up more than 50 scheduled messages: the 51st is refused with a clear error, so one account can't flood the sender.

## Done when
- [ ] `python3 -m unittest discover -s tests` -> OK
- [ ] `tests/test_limit.py` passes: scheduling a 51st message raises `QueueFull` with `status == 409`

## Out of scope
- per-user limits, a settings page

## Decisions
- the limit lives in `msgq/config.py` as `MAX_SCHEDULED` - one place to change it

## Open questions
- none

## Slices
- [x] 1. 51st scheduled message is refused with 409 - test: scheduling a 51st message raises `QueueFull` with `status == 409` - copy: `msgq/queue.py`
