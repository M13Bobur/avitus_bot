"""Unique supplier per branch for supplier users

Revision ID: 005
Revises: 004
Create Date: 2026-06-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  op.create_index(
    "uq_users_supplier_branch",
    "users",
    ["supplier_id", "branch_id"],
    unique=True,
    postgresql_where=sa.text(
      "role = 'supplier' AND supplier_id IS NOT NULL AND branch_id IS NOT NULL"
    ),
  )


def downgrade() -> None:
  op.drop_index("uq_users_supplier_branch", table_name="users")
