from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User, UserRole
from app.repositories.supplier import SupplierRepository
from app.repositories.user import UserRepository


class UserManagementService:
  def __init__(self, session: AsyncSession) -> None:
    self._session = session
    self._user_repo = UserRepository(session)
    self._supplier_repo = SupplierRepository(session)

  async def get_all_users(self) -> list[User]:
    return await self._user_repo.get_all_with_supplier()

  async def get_user(self, user_id: int) -> User | None:
    return await self._user_repo.get_with_supplier(user_id)

  async def search_users(self, query: str) -> list[User]:
    return await self._user_repo.search(query)

  async def create_user(
    self,
    telegram_id: int,
    full_name: str,
    role: UserRole,
    supplier_id: int | None = None,
  ) -> User:
    return await self._user_repo.create(
      telegram_id=telegram_id,
      full_name=full_name,
      role=role.value,
      supplier_id=supplier_id,
    )

  async def delete_user(self, user_id: int) -> User | None:
    user = await self._user_repo.get_by_id(user_id)
    if user is None:
      return None

    if user.supplier_id is not None:
      supplier = await self._supplier_repo.get_by_id(user.supplier_id)
      if supplier is not None and supplier.telegram_id == user.telegram_id:
        supplier.telegram_id = None

    await self._session.delete(user)
    await self._session.flush()
    return user


class SupplierManagementService:
  def __init__(self, session: AsyncSession) -> None:
    self._supplier_repo = SupplierRepository(session)

  async def get_all_suppliers(self) -> list:
    return await self._supplier_repo.get_all()

  async def get_active_suppliers(self) -> list:
    return await self._supplier_repo.get_active_suppliers()

  async def toggle_active(self, supplier_id: int) -> bool:
    supplier = await self._supplier_repo.get_by_id(supplier_id)
    if supplier is None:
      return False
    supplier.is_active = not supplier.is_active
    await self._supplier_repo._session.flush()
    return supplier.is_active
