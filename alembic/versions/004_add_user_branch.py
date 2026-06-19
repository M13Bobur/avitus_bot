"""Add branch_id to users

Revision ID: 004
Revises: 003
Create Date: 2026-06-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  op.add_column("users", sa.Column("branch_id", sa.Integer(), nullable=True))
  op.create_foreign_key(
    "fk_users_branch_id",
    "users",
    "branches",
    ["branch_id"],
    ["id"],
    ondelete="SET NULL",
  )
  op.create_index("ix_users_branch_id", "users", ["branch_id"])

  op.execute(
    """
    UPDATE users AS u
    SET branch_id = sub.branch_id
    FROM (
      SELECT
        u2.id AS user_id,
        (
          SELECT i.branch_id
          FROM inventory i
          WHERE i.supplier_id = u2.supplier_id
          GROUP BY i.branch_id
          ORDER BY MAX(i.updated_at) DESC
          LIMIT 1
        ) AS branch_id
      FROM users u2
      WHERE u2.role = 'supplier'
        AND u2.supplier_id IS NOT NULL
        AND u2.branch_id IS NULL
    ) AS sub
    WHERE u.id = sub.user_id
      AND sub.branch_id IS NOT NULL
    """
  )


def downgrade() -> None:
  op.drop_index("ix_users_branch_id", table_name="users")
  op.drop_constraint("fk_users_branch_id", "users", type_="foreignkey")
  op.drop_column("users", "branch_id")
