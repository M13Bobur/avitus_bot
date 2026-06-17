from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Medicine
from app.repositories.base import BaseRepository


class MedicineRepository(BaseRepository[Medicine]):
  def __init__(self, session: AsyncSession) -> None:
    super().__init__(session, Medicine)

  async def get_by_name(self, name: str) -> Medicine | None:
    result = await self._session.execute(
      select(Medicine).where(Medicine.name == name)
    )
    return result.scalar_one_or_none()

  async def get_or_create(self, name: str) -> Medicine:
    medicine = await self.get_by_name(name)
    if medicine is not None:
      return medicine
    return await self.create(name=name)

  async def search_by_name(self, query: str, limit: int = 50) -> list[Medicine]:
    result = await self._session.execute(
      select(Medicine).where(Medicine.name.ilike(f"%{query}%")).limit(limit)
    )
    return list(result.scalars().all())
