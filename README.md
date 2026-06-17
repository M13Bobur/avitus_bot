# Pharmacy Inventory Analytics Telegram Bot

Production-grade Telegram bot for pharmaceutical inventory analytics. Administrators upload Excel inventory reports; suppliers access only their own product data.

## Tech Stack

- Python 3.12+
- Aiogram 3.x
- PostgreSQL 16
- SQLAlchemy 2.x (async)
- Alembic
- Pandas + OpenPyXL
- Docker & Docker Compose
- Pydantic Settings
- Structlog (structured JSON logging)

## Architecture

```
app/
├── bot/              # Telegram layer (handlers, keyboards, middlewares)
├── database/         # SQLAlchemy models and engine
├── repositories/     # Data access layer (Repository Pattern)
├── services/         # Business logic (Service Layer)
├── config.py         # Environment configuration
├── logging_config.py # Structured logging setup
└── main.py           # Application entry point
```

Handlers contain no business logic. All data operations go through services and repositories.

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
```

Edit `.env` and set your Telegram bot token:

```
BOT_TOKEN=your_telegram_bot_token_here
```

### 2. Run with Docker Compose

```bash
docker compose up --build
```

This starts PostgreSQL and the bot. Alembic migrations run automatically on startup.

### 3. Seed admin user

```bash
docker compose exec bot python scripts/seed_admin.py <telegram_id> "Admin Name"
```

Get your Telegram ID from [@userinfobot](https://t.me/userinfobot).

### 4. Supplier self-registration (automatic)

Suppliers register in the bot:

1. Send `/start`
2. Enter registration password (default: `pharm2024`, set via `SUPPLIER_REGISTRATION_PASSWORD`)
3. Select company from list (companies come from Excel `Поставщик` column after admin upload)
4. Share phone number via Telegram button

On next `/start`, supplier sees their company inventory automatically.

Optional manual seed (legacy):

```bash
docker compose exec bot python scripts/seed_supplier.py <telegram_id> "Supplier Name" "Supplier Company Name"
```

## Local Development (without Docker)

### Prerequisites

- Python 3.12+
- PostgreSQL 16

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit DATABASE_URL for local PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://pharm_user:pharm_pass@localhost:5432/pharm_db

alembic upgrade head
python scripts/seed_admin.py <telegram_id> "Admin Name"
python -m app.main
```

## Excel Import Format

Upload `.xlsx` files with these columns (others are ignored):

| Column       | Description   |
|--------------|---------------|
| Филиал       | Branch        |
| Поставщик    | Supplier      |
| Дата         | Report date   |
| Наименование | Medicine name |
| Кол-во       | Quantity      |

Import behavior:

- Validates file format and required columns
- Normalizes text values
- Ignores duplicate rows within the same file
- Creates missing suppliers, branches, and medicines
- Upserts inventory records (no historical data deletion)
- Logs all imports with success/failure status
- Creates low-stock notifications when quantity < threshold

## Bot Features

### Admin Menu

| Button          | Description                              |
|-----------------|------------------------------------------|
| Upload Excel    | Import inventory from Excel file         |
| Statistics      | System-wide counts and last upload time  |
| Suppliers       | List all suppliers                       |
| Users           | List registered users                    |
| Settings        | View low-stock threshold                 |

Command: `/set_threshold <number>` — change low-stock threshold.

### Supplier Menu

| Button            | Description                              |
|-------------------|------------------------------------------|
| Inventory Report  | Totals: medicines, stock, branches       |
| Branch Report     | Inventory grouped by branch              |
| Download Excel    | Export supplier-owned inventory as Excel |
| Search Medicine   | Search by medicine name, grouped by branch |

Suppliers only see data linked to their supplier account.

## Environment Variables

| Variable              | Default                                      | Description                |
|-----------------------|----------------------------------------------|----------------------------|
| `BOT_TOKEN`           | —                                            | Telegram bot token         |
| `DATABASE_URL`        | `postgresql+asyncpg://...@postgres:5432/...` | Async PostgreSQL URL       |
| `LOG_LEVEL`           | `INFO`                                       | Logging level              |
| `MAX_UPLOAD_SIZE_MB`  | `20`                                         | Max Excel upload size (MB) |
| `LOW_STOCK_THRESHOLD` | `20`                                         | Low-stock alert threshold  |

## Database Schema

- `users` — Telegram users with roles (`super_admin`, `supplier`)
- `suppliers` — Medicine manufacturers/distributors
- `branches` — Pharmacy branches
- `medicines` — Medicine catalog
- `inventory` — Inventory snapshots (supplier + branch + medicine + date)
- `import_logs` — Excel import audit trail
- `notifications` — Low-stock notification records
- `app_settings` — Runtime configuration (e.g. threshold)

## Security

- Only pre-registered users can access the bot
- Role-based menu and handler filtering
- Supplier data isolation at query level (`supplier_id` filter)
- File size limits on uploads
- Excel format validation before processing
- Input normalization and validation

## Logging

Structured JSON logs via structlog. Key events:

- `import_completed` / `import_failed` — Excel imports
- `admin_upload_success` / `admin_upload_failed` — Admin uploads
- `supplier_export` / `supplier_export_failed` — Excel exports
- `excel_parsed` — File parsing results

## License

Private — internal use only.
