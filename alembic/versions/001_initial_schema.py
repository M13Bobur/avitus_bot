"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  op.create_table(
    "suppliers",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("name", sa.String(length=255), nullable=False),
    sa.Column("telegram_id", sa.BigInteger(), nullable=True),
    sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("name"),
  )
  op.create_index("ix_suppliers_name", "suppliers", ["name"])
  op.create_index("ix_suppliers_telegram_id", "suppliers", ["telegram_id"])

  op.create_table(
    "branches",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("name", sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("name"),
  )
  op.create_index("ix_branches_name", "branches", ["name"])

  op.create_table(
    "medicines",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("name", sa.String(length=500), nullable=False),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("name"),
  )
  op.create_index("ix_medicines_name", "medicines", ["name"])

  op.create_table(
    "users",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("telegram_id", sa.BigInteger(), nullable=False),
    sa.Column("full_name", sa.String(length=255), nullable=False),
    sa.Column("role", sa.String(length=50), nullable=False),
    sa.Column("supplier_id", sa.Integer(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="SET NULL"),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("telegram_id"),
  )
  op.create_index("ix_users_telegram_id", "users", ["telegram_id"])

  op.create_table(
    "inventory",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("supplier_id", sa.Integer(), nullable=False),
    sa.Column("branch_id", sa.Integer(), nullable=False),
    sa.Column("medicine_id", sa.Integer(), nullable=False),
    sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("report_date", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
    sa.ForeignKeyConstraint(["medicine_id"], ["medicines.id"], ondelete="CASCADE"),
    sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint(
      "supplier_id", "branch_id", "medicine_id", "report_date",
      name="uq_inventory_supplier_branch_medicine_date",
    ),
  )
  op.create_index("ix_inventory_supplier_id", "inventory", ["supplier_id"])
  op.create_index("ix_inventory_branch_id", "inventory", ["branch_id"])
  op.create_index("ix_inventory_medicine_id", "inventory", ["medicine_id"])
  op.create_index("ix_inventory_report_date", "inventory", ["report_date"])

  op.create_table(
    "import_logs",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("user_id", sa.Integer(), nullable=True),
    sa.Column("file_name", sa.String(length=500), nullable=False),
    sa.Column("rows_processed", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("rows_skipped", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("status", sa.String(length=50), nullable=False),
    sa.Column("error_message", sa.Text(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    sa.PrimaryKeyConstraint("id"),
  )

  op.create_table(
    "notifications",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("supplier_id", sa.Integer(), nullable=False),
    sa.Column("medicine_id", sa.Integer(), nullable=False),
    sa.Column("branch_id", sa.Integer(), nullable=False),
    sa.Column("quantity", sa.Integer(), nullable=False),
    sa.Column("threshold", sa.Integer(), nullable=False),
    sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
    sa.ForeignKeyConstraint(["medicine_id"], ["medicines.id"], ondelete="CASCADE"),
    sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
  )
  op.create_index("ix_notifications_supplier_id", "notifications", ["supplier_id"])

  op.create_table(
    "app_settings",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("key", sa.String(length=100), nullable=False),
    sa.Column("value", sa.String(length=500), nullable=False),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("key"),
  )


def downgrade() -> None:
  op.drop_table("app_settings")
  op.drop_index("ix_notifications_supplier_id", table_name="notifications")
  op.drop_table("notifications")
  op.drop_table("import_logs")
  op.drop_index("ix_inventory_report_date", table_name="inventory")
  op.drop_index("ix_inventory_medicine_id", table_name="inventory")
  op.drop_index("ix_inventory_branch_id", table_name="inventory")
  op.drop_index("ix_inventory_supplier_id", table_name="inventory")
  op.drop_table("inventory")
  op.drop_index("ix_users_telegram_id", table_name="users")
  op.drop_table("users")
  op.drop_index("ix_medicines_name", table_name="medicines")
  op.drop_table("medicines")
  op.drop_index("ix_branches_name", table_name="branches")
  op.drop_table("branches")
  op.drop_index("ix_suppliers_telegram_id", table_name="suppliers")
  op.drop_index("ix_suppliers_name", table_name="suppliers")
  op.drop_table("suppliers")
