from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Branch
from app.repositories.base import BaseRepository


class BranchRepository(BaseRepository[Branch]):
  def __init__(self, session: AsyncSession) -> None:
    super().__init__(session, Branch)

  async def get_by_name(self, name: str) -> Branch | None:
    result = await self._session.execute(
      select(Branch).where(Branch.name == name)
    )
    return result.scalar_one_or_none()

  async def get_or_create(self, name: str) -> Branch:
    branch = await self.get_by_name(name)
    if branch is not None:
      return branch
    return await self.create(name=name)
