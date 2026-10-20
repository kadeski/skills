# Caching

Responses from slow targets are cached for 60 seconds, keyed by URL and body hash. The cache lives in memory, one per process. Set `CACHE_TTL` to change the time, or pass `--no-cache` to turn it off for one run.
