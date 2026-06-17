from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User, UserRole
from app.repositories.branch import BranchRepository
from app.repositories.import_log import ImportLogRepository
from app.repositories.inventory import InventoryRepository
from app.repositories.medicine import MedicineRepository
from app.repositories.supplier import SupplierRepository
from app.repositories.user import UserRepository


class AuthService:
  def __init__(self, session: AsyncSession) -> None:
    self._user_repo = UserRepository(session)

  async def get_user(self, telegram_id: int) -> User | None:
    return await self._user_repo.get_by_telegram_id(telegram_id)

  async def is_authorized(self, telegram_id: int) -> bool:
    user = await self.get_user(telegram_id)
    return user is not None

  async def is_super_admin(self, telegram_id: int) -> bool:
    user = await self.get_user(telegram_id)
    return user is not None and user.role == UserRole.SUPER_ADMIN.value

  async def is_supplier(self, telegram_id: int) -> bool:
    user = await self.get_user(telegram_id)
    return user is not None and user.role == UserRole.SUPPLIER.value

  async def get_supplier_id(self, telegram_id: int) -> int | None:
    user = await self.get_user(telegram_id)
    if user is None or user.role != UserRole.SUPPLIER.value:
      return None
    return user.supplier_id


class StatsService:
  def __init__(self, session: AsyncSession) -> None:
    self._supplier_repo = SupplierRepository(session)
    self._medicine_repo = MedicineRepository(session)
    self._branch_repo = BranchRepository(session)
    self._inventory_repo = InventoryRepository(session)
    self._import_log_repo = ImportLogRepository(session)

  async def get_statistics(self) -> dict[str, int | str | None]:
    last_upload = await self._import_log_repo.get_last_upload()
    last_update = await self._inventory_repo.get_last_update()

    return {
      "total_suppliers": await self._supplier_repo.count(),
      "total_medicines": await self._medicine_repo.count(),
      "total_branches": await self._branch_repo.count(),
      "total_inventory_records": await self._inventory_repo.count(),
      "last_upload_time": (
        last_upload.created_at.strftime("%Y-%m-%d %H:%M") if last_upload else None
      ),
      "last_update_time": (
        last_update.strftime("%Y-%m-%d %H:%M") if last_update else None
      ),
    }
