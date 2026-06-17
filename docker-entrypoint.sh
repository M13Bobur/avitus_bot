#!/bin/sh
set -e

python scripts/wait_for_db.py
alembic upgrade head
exec python -m app.main
