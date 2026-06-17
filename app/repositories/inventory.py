from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Branch, Inventory, Medicine
from app.repositories.base import BaseRepository


class InventoryRepository(BaseRepository[Inventory]):
  def __init__(self, session: AsyncSession) -> None:
    super().__init__(session, Inventory)

  async def upsert(
    self,
    supplier_id: int,
    branch_id: int,
    medicine_id: int,
    quantity: Decimal,
    report_date: datetime,
  ) -> None:
    stmt = insert(Inventory).values(
      supplier_id=supplier_id,
      branch_id=branch_id,
      medicine_id=medicine_id,
      quantity=quantity,
      report_date=report_date,
    )
    stmt = stmt.on_conflict_do_update(
      constraint="uq_inventory_supplier_branch_medicine_date",
      set_={
        "quantity": quantity,
        "updated_at": func.now(),
      },
    )
    await self._session.execute(stmt)

  async def get_by_supplier(self, supplier_id: int) -> list[Inventory]:
    result = await self._session.execute(
      select(Inventory)
      .options(
        selectinload(Inventory.branch),
        selectinload(Inventory.medicine),
      )
      .where(Inventory.supplier_id == supplier_id)
      .order_by(Inventory.branch_id, Inventory.medicine_id)
    )
    return list(result.scalars().all())

  async def get_by_supplier_and_medicine(
    self, supplier_id: int, medicine_id: int
  ) -> list[Inventory]:
    result = await self._session.execute(
      select(Inventory)
      .options(selectinload(Inventory.branch), selectinload(Inventory.medicine))
      .where(
        Inventory.supplier_id == supplier_id,
        Inventory.medicine_id == medicine_id,
      )
      .order_by(Inventory.branch_id)
    )
    return list(result.scalars().all())

  async def get_supplier_summary(self, supplier_id: int) -> dict[str, int | datetime | None]:
    result = await self._session.execute(
      select(
        func.count(func.distinct(Inventory.medicine_id)).label("total_medicines"),
        func.sum(Inventory.quantity).label("total_stock"),
        func.count(func.distinct(Inventory.branch_id)).label("branch_count"),
        func.max(Inventory.updated_at).label("last_update"),
      ).where(Inventory.supplier_id == supplier_id)
    )
    row = result.one()
    return {
      "total_medicines": row.total_medicines or 0,
      "total_stock": Decimal(row.total_stock or 0),
      "branch_count": row.branch_count or 0,
      "last_update": row.last_update,
    }

  async def get_by_supplier_grouped_by_branch(
    self, supplier_id: int
  ) -> list[tuple[Branch, list[tuple[Medicine, Decimal]]]]:
    records = await self.get_by_supplier(supplier_id)
    branch_map: dict[int, tuple[Branch, list[tuple[Medicine, Decimal]]]] = {}

    for record in records:
      if record.branch_id not in branch_map:
        branch_map[record.branch_id] = (record.branch, [])
      branch_map[record.branch_id][1].append((record.medicine, record.quantity))

    return list(branch_map.values())

  async def get_low_stock(
    self, supplier_id: int, threshold: int
  ) -> list[Inventory]:
    result = await self._session.execute(
      select(Inventory)
      .options(
        selectinload(Inventory.branch),
        selectinload(Inventory.medicine),
      )
      .where(
        Inventory.supplier_id == supplier_id,
        Inventory.quantity < threshold,
      )
    )
    return list(result.scalars().all())

  async def get_last_update(self) -> datetime | None:
    result = await self._session.execute(
      select(func.max(Inventory.updated_at))
    )
    return result.scalar_one_or_none()
