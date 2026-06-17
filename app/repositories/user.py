from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Supplier, User, UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
  def __init__(self, session: AsyncSession) -> None:
    super().__init__(session, User)

  async def get_by_telegram_id(self, telegram_id: int) -> User | None:
    result = await self._session.execute(
      select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()

  async def get_all_by_role(self, role: UserRole) -> list[User]:
    result = await self._session.execute(
      select(User).where(User.role == role.value)
    )
    return list(result.scalars().all())

  async def get_all_with_supplier(self) -> list[User]:
    result = await self._session.execute(
      select(User).options(selectinload(User.supplier)).order_by(User.id)
    )
    return list(result.scalars().all())

  async def get_with_supplier(self, user_id: int) -> User | None:
    result = await self._session.execute(
      select(User).options(selectinload(User.supplier)).where(User.id == user_id)
    )
    return result.scalar_one_or_none()

  async def search(self, query: str) -> list[User]:
    pattern = f"%{query}%"
    result = await self._session.execute(
      select(User)
      .options(selectinload(User.supplier))
      .outerjoin(Supplier, User.supplier_id == Supplier.id)
      .where(
        or_(
          User.full_name.ilike(pattern),
          User.phone.ilike(pattern),
          Supplier.name.ilike(pattern),
        )
      )
      .order_by(User.id)
    )
    return list(result.scalars().all())
