from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User, UserRole
from app.repositories.branch import BranchRepository
from app.repositories.inventory import InventoryRepository
from app.repositories.user import UserRepository


class SupplierContextError(Exception):
  pass


class SupplierBranchContext:
  def __init__(self, branch_id: int, branch_name: str) -> None:
    self.branch_id = branch_id
    self.branch_name = branch_name


class SupplierContextService:
  def __init__(self, session: AsyncSession) -> None:
    self._session = session
    self._user_repo = UserRepository(session)
    self._branch_repo = BranchRepository(session)
    self._inventory_repo = InventoryRepository(session)

  async def resolve_branch_id(self, user: User) -> int | None:
    if user.branch_id is not None:
      return user.branch_id

    if user.supplier_id is None:
      return None

    return await self._inventory_repo.get_primary_branch_id_for_supplier(user.supplier_id)

  async def require_branch_id(self, user: User) -> int:
    branch_id = await self.resolve_branch_id(user)
    if branch_id is None:
      raise SupplierContextError(
        "Филиал аниқланмади. Админ билан боғланинг ёки қайта рўйхатдан ўтинг."
      )
    return branch_id

  async def require_branch_context(self, user: User) -> SupplierBranchContext:
    branch_id = await self.require_branch_id(user)
    if user.branch is not None and user.branch_id == branch_id:
      return SupplierBranchContext(branch_id, user.branch.name)

    branch = await self._branch_repo.get_by_id(branch_id)
    if branch is None:
      raise SupplierContextError(
        "Филиал аниқланмади. Админ билан боғланинг ёки қайта рўйхатдан ўтинг."
      )
    return SupplierBranchContext(branch_id, branch.name)

  async def get_busy_supplier_ids(self, branch_id: int) -> set[int]:
    return await self._user_repo.get_registered_supplier_ids_for_branch(branch_id)

  async def get_supplier_telegram_id(
    self, supplier_id: int, branch_id: int
  ) -> int | None:
    user = await self._user_repo.get_supplier_user_for_branch(supplier_id, branch_id)
    if user is None:
      return None
    return user.telegram_id

  async def is_supplier_registered_for_branch(
    self, supplier_id: int, branch_id: int
  ) -> bool:
    user = await self._user_repo.get_supplier_user_for_branch(supplier_id, branch_id)
    return user is not None
