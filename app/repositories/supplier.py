from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Inventory, Supplier
from app.repositories.base import BaseRepository


class SupplierRepository(BaseRepository[Supplier]):
  def __init__(self, session: AsyncSession) -> None:
    super().__init__(session, Supplier)

  async def get_by_name(self, name: str) -> Supplier | None:
    result = await self._session.execute(
      select(Supplier).where(Supplier.name == name)
    )
    return result.scalar_one_or_none()

  async def get_active_suppliers(self) -> list[Supplier]:
    result = await self._session.execute(
      select(Supplier).where(Supplier.is_active.is_(True))
    )
    return list(result.scalars().all())

  async def get_active_suppliers_for_branch(self, branch_id: int) -> list[Supplier]:
    result = await self._session.execute(
      select(Supplier)
      .join(Inventory, Inventory.supplier_id == Supplier.id)
      .where(
        Inventory.branch_id == branch_id,
        Supplier.is_active.is_(True),
      )
      .distinct()
    )
    return list(result.scalars().all())

  async def get_or_create(self, name: str) -> Supplier:
    supplier = await self.get_by_name(name)
    if supplier is not None:
      return supplier
    return await self.create(name=name, is_active=True)
