"""Quantity columns to decimal

Revision ID: 003
Revises: 002
Create Date: 2026-06-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  op.alter_column(
    "inventory",
    "quantity",
    existing_type=sa.Integer(),
    type_=sa.Numeric(12, 3),
    existing_nullable=False,
    postgresql_using="quantity::numeric(12,3)",
  )
  op.alter_column(
    "notifications",
    "quantity",
    existing_type=sa.Integer(),
    type_=sa.Numeric(12, 3),
    existing_nullable=False,
    postgresql_using="quantity::numeric(12,3)",
  )


def downgrade() -> None:
  op.alter_column(
    "notifications",
    "quantity",
    existing_type=sa.Numeric(12, 3),
    type_=sa.Integer(),
    existing_nullable=False,
    postgresql_using="quantity::integer",
  )
  op.alter_column(
    "inventory",
    "quantity",
    existing_type=sa.Numeric(12, 3),
    type_=sa.Integer(),
    existing_nullable=False,
    postgresql_using="quantity::integer",
  )
