from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import SupportMessage, User
from app.repositories.base import BaseRepository


@dataclass(frozen=True)
class MessageConversation:
  user: User
  unread_count: int
  total_count: int
  last_message_at: datetime


class SupportMessageRepository(BaseRepository[SupportMessage]):
  def __init__(self, session: AsyncSession) -> None:
    super().__init__(session, SupportMessage)

  async def create_message(self, user_id: int, text: str) -> SupportMessage:
    return await self.create(user_id=user_id, text=text)

  async def get_conversations(self) -> list[MessageConversation]:
    stats = (
      select(
        SupportMessage.user_id,
        func.count().label("total_count"),
        func.count()
        .filter(SupportMessage.is_read.is_(False))
        .label("unread_count"),
        func.max(SupportMessage.created_at).label("last_message_at"),
      )
      .group_by(SupportMessage.user_id)
      .subquery()
    )

    result = await self._session.execute(
      select(
        User,
        stats.c.unread_count,
        stats.c.total_count,
        stats.c.last_message_at,
      )
      .join(stats, User.id == stats.c.user_id)
      .options(selectinload(User.supplier), selectinload(User.branch))
      .order_by(stats.c.last_message_at.desc())
    )

    return [
      MessageConversation(
        user=row[0],
        unread_count=row[1],
        total_count=row[2],
        last_message_at=row[3],
      )
      for row in result.all()
    ]

  async def get_by_user_id(self, user_id: int) -> list[SupportMessage]:
    result = await self._session.execute(
      select(SupportMessage)
      .where(SupportMessage.user_id == user_id)
      .order_by(SupportMessage.created_at.asc())
    )
    return list(result.scalars().all())

  async def mark_as_read(self, user_id: int) -> int:
    result = await self._session.execute(
      update(SupportMessage)
      .where(
        SupportMessage.user_id == user_id,
        SupportMessage.is_read.is_(False),
      )
      .values(is_read=True)
    )
    return result.rowcount or 0

  async def count_total_unread(self) -> int:
    result = await self._session.execute(
      select(func.count())
      .select_from(SupportMessage)
      .where(SupportMessage.is_read.is_(False))
    )
    return result.scalar_one()
