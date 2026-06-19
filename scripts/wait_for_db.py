#!/usr/bin/env python3
"""Wait until PostgreSQL is reachable before running migrations."""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH, encoding="utf-8")

MAX_ATTEMPTS = 60
SLEEP_SECONDS = 2


def format_error(exc: BaseException) -> str:
  try:
    message = str(exc)
    if message:
      return message
  except UnicodeDecodeError:
    pass
  return repr(exc)


def main() -> None:
  database_url = os.environ.get("DATABASE_URL", "").strip()
  if not database_url:
    print("DATABASE_URL is not set")
    print(f"Create {ENV_PATH} from .env.example (save as UTF-8).")
    sys.exit(1)

  sync_url = database_url.replace("+asyncpg", "+psycopg2", 1)

  for attempt in range(1, MAX_ATTEMPTS + 1):
    try:
      engine = create_engine(sync_url, pool_pre_ping=True)
      with engine.connect():
        print("Database is ready")
        sys.exit(0)
    except Exception as exc:
      print(f"Waiting for database ({attempt}/{MAX_ATTEMPTS}): {format_error(exc)}")
      time.sleep(SLEEP_SECONDS)

  print("Database not reachable")
  sys.exit(1)


if __name__ == "__main__":
  main()
