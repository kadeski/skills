# Design

## Upload path

Clients send files in 8 MB chunks. A node writes chunks to local disk, then moves the finished file to object storage.

## Limits

The load test on {{d-3}} found that a node keeps p95 chunk latency under 2 s up to 32 concurrent uploads, so the limit is 32. It is set by `max_uploads` in `config/defaults.toml`.
