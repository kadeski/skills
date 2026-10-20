import os
import sys

TTL = int(os.environ.get("CACHE_TTL", 60))  # seconds
ENABLED = "--no-cache" not in sys.argv
