from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ImportLog
from app.repositories.base import BaseRepository


class ImportLogRepository(BaseRepository[ImportLog]):
  def __init__(self, session: AsyncSession) -> None:
    super().__init__(session, ImportLog)

  async def get_last_upload(self) -> ImportLog | None:
    result = await self._session.execute(
      select(ImportLog)
      .where(ImportLog.status == "success")
      .order_by(ImportLog.created_at.desc())
      .limit(1)
    )
    return result.scalar_one_or_none()
