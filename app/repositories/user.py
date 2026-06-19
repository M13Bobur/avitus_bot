from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Branch, Supplier, User, UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
  def __init__(self, session: AsyncSession) -> None:
    super().__init__(session, User)

  async def get_by_telegram_id(self, telegram_id: int) -> User | None:
    result = await self._session.execute(
      select(User)
      .options(
        selectinload(User.supplier),
        selectinload(User.branch),
      )
      .where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()

  async def get_supplier_user_for_branch(
    self, supplier_id: int, branch_id: int
  ) -> User | None:
    result = await self._session.execute(
      select(User)
      .where(
        User.role == UserRole.SUPPLIER.value,
        User.supplier_id == supplier_id,
        User.branch_id == branch_id,
      )
      .limit(1)
    )
    return result.scalar_one_or_none()

  async def get_registered_supplier_ids_for_branch(self, branch_id: int) -> set[int]:
    result = await self._session.execute(
      select(User.supplier_id).where(
        User.role == UserRole.SUPPLIER.value,
        User.branch_id == branch_id,
        User.supplier_id.is_not(None),
      )
    )
    return {row[0] for row in result.all()}

  async def get_all_by_role(self, role: UserRole) -> list[User]:
    result = await self._session.execute(
      select(User).where(User.role == role.value)
    )
    return list(result.scalars().all())

  async def get_all_with_supplier(self) -> list[User]:
    result = await self._session.execute(
      select(User)
      .options(selectinload(User.supplier), selectinload(User.branch))
      .order_by(User.id)
    )
    return list(result.scalars().all())

  async def get_with_supplier(self, user_id: int) -> User | None:
    result = await self._session.execute(
      select(User)
      .options(selectinload(User.supplier), selectinload(User.branch))
      .where(User.id == user_id)
    )
    return result.scalar_one_or_none()

  async def search(self, query: str) -> list[User]:
    pattern = f"%{query}%"
    result = await self._session.execute(
      select(User)
      .options(selectinload(User.supplier), selectinload(User.branch))
      .outerjoin(Supplier, User.supplier_id == Supplier.id)
      .outerjoin(Branch, User.branch_id == Branch.id)
      .where(
        or_(
          User.full_name.ilike(pattern),
          User.phone.ilike(pattern),
          Supplier.name.ilike(pattern),
          Branch.name.ilike(pattern),
        )
      )
      .order_by(User.id)
    )
    return list(result.scalars().all())
