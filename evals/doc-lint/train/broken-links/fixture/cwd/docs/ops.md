# Operations

## Running on a schedule

Run `tally daily` from cron at 00:05. It reads yesterday's logs and writes the summary next to them.

## Rolling back

Keep the last two binaries. To roll back, point the cron entry at the older one and rerun `tally daily` for the missed day.
