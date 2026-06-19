from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Inventory, Notification, User, UserRole
from app.repositories.branch import BranchRepository
from app.repositories.supplier import SupplierRepository
from app.repositories.user import UserRepository


class BranchManagementError(Exception):
  pass


class BranchManagementService:
  def __init__(self, session: AsyncSession) -> None:
    self._session = session
    self._branch_repo = BranchRepository(session)

  async def get_all_branches(self) -> list:
    return await self._branch_repo.get_all_ordered()

  async def get_branch(self, branch_id: int):
    return await self._branch_repo.get_by_id(branch_id)

  async def get_branch_stats(self, branch_id: int) -> dict[str, int]:
    inventory_result = await self._session.execute(
      select(func.count()).select_from(Inventory).where(Inventory.branch_id == branch_id)
    )
    users_result = await self._session.execute(
      select(func.count())
      .select_from(User)
      .where(User.branch_id == branch_id, User.role == UserRole.SUPPLIER.value)
    )
    return {
      "inventory_records": inventory_result.scalar_one(),
      "supplier_users": users_result.scalar_one(),
    }

  async def create_branch(self, name: str):
    name = name.strip()
    if not name:
      raise BranchManagementError("Филиал номи бўш бўлмаслиги керак.")

    existing = await self._branch_repo.get_by_name(name)
    if existing is not None:
      raise BranchManagementError("Бу номли филиал аллақачон мавжуд.")

    return await self._branch_repo.create(name=name)

  async def delete_branch(self, branch_id: int):
    branch = await self._branch_repo.get_by_id(branch_id)
    if branch is None:
      raise BranchManagementError("Филиал топилмади.")

    stats = await self.get_branch_stats(branch_id)

    await self._session.execute(
      delete(Notification).where(Notification.branch_id == branch_id)
    )
    await self._session.execute(
      delete(Inventory).where(Inventory.branch_id == branch_id)
    )
    await self._session.execute(
      update(User).where(User.branch_id == branch_id).values(branch_id=None)
    )
    await self._session.delete(branch)
    await self._session.flush()
    return branch, stats


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
