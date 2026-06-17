from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.logging_config import get_logger
from app.repositories.branch import BranchRepository
from app.repositories.import_log import ImportLogRepository
from app.repositories.inventory import InventoryRepository
from app.repositories.medicine import MedicineRepository
from app.repositories.notification import NotificationRepository
from app.repositories.supplier import SupplierRepository
from app.services.app_settings import AppSettingsService
from app.services.excel_import import ExcelImportError, ExcelImportService, ImportRow

logger = get_logger(__name__)


@dataclass
class SupplierLowStockAlert:
  supplier_id: int
  supplier_name: str
  telegram_id: int | None
  threshold: int
  items: list[tuple[str, str, Decimal]] = field(default_factory=list)


class InventoryService:
  def __init__(self, session: AsyncSession) -> None:
    self._session = session
    self._supplier_repo = SupplierRepository(session)
    self._branch_repo = BranchRepository(session)
    self._medicine_repo = MedicineRepository(session)
    self._inventory_repo = InventoryRepository(session)
    self._import_log_repo = ImportLogRepository(session)
    self._notification_repo = NotificationRepository(session)
    self._app_settings = AppSettingsService(session)
    self._excel_import = ExcelImportService()

  async def get_low_stock_threshold(self) -> int:
    return await self._app_settings.get_low_stock_threshold()

  async def set_low_stock_threshold(self, threshold: int) -> None:
    await self._app_settings.set_low_stock_threshold(threshold)

  async def import_excel(
    self, file_path: str, file_name: str, user: User
  ) -> tuple[int, int, list[SupplierLowStockAlert]]:
    try:
      rows = self._excel_import.validate_and_read(file_path, file_name)
    except ExcelImportError as exc:
      await self._import_log_repo.create(
        user_id=user.id,
        file_name=file_name,
        rows_processed=0,
        rows_skipped=0,
        status="failed",
        error_message=str(exc),
      )
      logger.error(
        "import_failed",
        user_id=user.id,
        file_name=file_name,
        error=str(exc),
      )
      raise

    processed = 0
    skipped = 0
    threshold = await self.get_low_stock_threshold()

    supplier_cache: dict[str, int] = {}
    branch_cache: dict[str, int] = {}
    medicine_cache: dict[str, int] = {}
    alerts: dict[int, SupplierLowStockAlert] = {}

    for row in rows:
      try:
        await self._process_row(
          row, supplier_cache, branch_cache, medicine_cache, threshold, alerts
        )
        processed += 1
      except Exception as exc:
        await self._session.rollback()
        skipped += 1
        logger.warning("import_row_failed", error=str(exc), medicine=row.medicine)

    await self._import_log_repo.create(
      user_id=user.id,
      file_name=file_name,
      rows_processed=processed,
      rows_skipped=skipped,
      status="success",
    )

    logger.info(
      "import_completed",
      user_id=user.id,
      file_name=file_name,
      processed=processed,
      skipped=skipped,
      low_stock_suppliers=sum(1 for a in alerts.values() if a.items),
    )
    return processed, skipped, [alert for alert in alerts.values() if alert.items]

  async def _process_row(
    self,
    row: ImportRow,
    supplier_cache: dict[str, int],
    branch_cache: dict[str, int],
    medicine_cache: dict[str, int],
    threshold: int,
    alerts: dict[int, SupplierLowStockAlert],
  ) -> None:
    supplier_id = supplier_cache.get(row.supplier)
    if supplier_id is None:
      supplier = await self._supplier_repo.get_or_create(row.supplier)
      supplier_id = supplier.id
      supplier_cache[row.supplier] = supplier_id
      if supplier_id not in alerts:
        alerts[supplier_id] = SupplierLowStockAlert(
          supplier_id=supplier_id,
          supplier_name=supplier.name,
          telegram_id=supplier.telegram_id,
          threshold=threshold,
        )

    branch_id = branch_cache.get(row.branch)
    if branch_id is None:
      branch = await self._branch_repo.get_or_create(row.branch)
      branch_id = branch.id
      branch_cache[row.branch] = branch_id

    medicine_id = medicine_cache.get(row.medicine)
    if medicine_id is None:
      medicine = await self._medicine_repo.get_or_create(row.medicine)
      medicine_id = medicine.id
      medicine_cache[row.medicine] = medicine_id

    await self._inventory_repo.upsert(
      supplier_id=supplier_id,
      branch_id=branch_id,
      medicine_id=medicine_id,
      quantity=row.quantity,
      report_date=row.report_date,
    )

    if row.quantity < threshold:
      try:
        await self._notification_repo.create_notification(
          supplier_id=supplier_id,
          medicine_id=medicine_id,
          branch_id=branch_id,
          quantity=row.quantity,
          threshold=threshold,
        )
      except Exception as exc:
        logger.warning("notification_create_failed", error=str(exc), medicine=row.medicine)

      alert = alerts.get(supplier_id)
      if alert is not None:
        alert.items.append((row.medicine, row.branch, row.quantity))

  async def get_supplier_summary(self, supplier_id: int) -> dict[str, int | datetime | None]:
    return await self._inventory_repo.get_supplier_summary(supplier_id)

  async def get_branch_report(self, supplier_id: int) -> list[tuple[str, list[tuple[str, int]]]]:
    grouped = await self._inventory_repo.get_by_supplier_grouped_by_branch(supplier_id)
    return [
      (branch.name, [(medicine.name, qty) for medicine, qty in items])
      for branch, items in grouped
    ]

  async def search_medicine(
    self, supplier_id: int, query: str
  ) -> list[tuple[str, list[tuple[str, int]]]]:
    medicines = await self._medicine_repo.search_by_name(query)
    if not medicines:
      return []

    results: list[tuple[str, list[tuple[str, int]]]] = []
    for medicine in medicines:
      records = await self._inventory_repo.get_by_supplier_and_medicine(
        supplier_id, medicine.id
      )
      branch_quantities = [(record.branch.name, record.quantity) for record in records]
      if branch_quantities:
        results.append((medicine.name, branch_quantities))

    return results
