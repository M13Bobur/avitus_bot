#!/usr/bin/env python3
"""Wait until PostgreSQL is reachable before running migrations."""

import os
import sys
import time

from sqlalchemy import create_engine

MAX_ATTEMPTS = 60
SLEEP_SECONDS = 2


def main() -> None:
  database_url = os.environ.get("DATABASE_URL", "")
  if not database_url:
    print("DATABASE_URL is not set")
    sys.exit(1)

  sync_url = database_url.replace("+asyncpg", "")

  for attempt in range(1, MAX_ATTEMPTS + 1):
    try:
      engine = create_engine(sync_url, pool_pre_ping=True)
      with engine.connect():
        print("Database is ready")
        sys.exit(0)
    except Exception as exc:
      print(f"Waiting for database ({attempt}/{MAX_ATTEMPTS}): {exc}")
      time.sleep(SLEEP_SECONDS)

  print("Database not reachable")
  sys.exit(1)


if __name__ == "__main__":
  main()
