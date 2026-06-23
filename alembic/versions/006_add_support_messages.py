"""Add support messages table

Revision ID: 006
Revises: 005
Create Date: 2026-06-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  op.create_table(
    "support_messages",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("user_id", sa.Integer(), nullable=False),
    sa.Column("text", sa.Text(), nullable=False),
    sa.Column("is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    sa.Column(
      "created_at",
      sa.DateTime(timezone=True),
      server_default=sa.text("now()"),
      nullable=False,
    ),
    sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
  )
  op.create_index("ix_support_messages_user_id", "support_messages", ["user_id"])
  op.create_index(
    "ix_support_messages_user_id_created_at",
    "support_messages",
    ["user_id", "created_at"],
  )
  op.create_index(
    "ix_support_messages_user_id_unread",
    "support_messages",
    ["user_id"],
    postgresql_where=sa.text("is_read = false"),
  )


def downgrade() -> None:
  op.drop_index("ix_support_messages_user_id_unread", table_name="support_messages")
  op.drop_index("ix_support_messages_user_id_created_at", table_name="support_messages")
  op.drop_index("ix_support_messages_user_id", table_name="support_messages")
  op.drop_table("support_messages")
