#!/usr/bin/env bash
set -euo pipefail

BACKUP_FILE="${1:-backup.sql}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-pharm_postgres}"
DB_USER="${DB_USER:-pharm_user}"
DB_NAME="${DB_NAME:-pharm_db}"

if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "Backup fayl topilmadi: $BACKUP_FILE"
  echo "Foydalanish: ./scripts/import_backup.sh [backup.sql]"
  exit 1
fi

echo "==> Bot to'xtatilmoqda..."
docker compose -f "$COMPOSE_FILE" stop bot

echo "==> Eski bazani o'chirish..."
docker exec "$POSTGRES_CONTAINER" psql -U "$DB_USER" -d postgres -c \
  "DROP DATABASE IF EXISTS ${DB_NAME} WITH (FORCE);"

echo "==> Yangi baza yaratilmoqda..."
docker exec "$POSTGRES_CONTAINER" psql -U "$DB_USER" -d postgres -c \
  "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

echo "==> Backup import qilinmoqda: $BACKUP_FILE"
sed '/^\\restrict /d; /^\\unrestrict /d' "$BACKUP_FILE" | \
  docker exec -i "$POSTGRES_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1

echo "==> Bot qayta ishga tushirilmoqda..."
docker compose -f "$COMPOSE_FILE" start bot

echo "==> Tayyor!"
