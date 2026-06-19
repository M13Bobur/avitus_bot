import os
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message

from app.bot.filters.role import IsSupplier
from app.bot.keyboards.menus import supplier_menu_keyboard
from app.bot.states.supplier import SupplierStates
from app.bot.texts import (
  BTN_BRANCH_REPORT,
  BTN_DOWNLOAD_EXCEL,
  BTN_INVENTORY_REPORT,
  BTN_SEARCH_MEDICINE,
  LABEL_NOT_AVAILABLE,
)
from app.database.models import User
from app.logging_config import get_logger
from app.repositories.inventory import InventoryRepository
from app.services.excel_export import ExcelExportService
from app.services.inventory import InventoryService
from app.services.supplier_context import SupplierContextError, SupplierContextService
from app.utils.quantity import format_quantity
from app.utils.telegram import split_message_parts

logger = get_logger(__name__)

router = Router(name="supplier")
router.message.filter(IsSupplier())


async def _send_long_text(message: Message, lines: list[str], **kwargs) -> None:
  parts = split_message_parts(lines)
  for index, part in enumerate(parts):
    if index > 0:
      part = f"📄 Давоми ({index + 1}):\n\n{part}"
    await message.answer(part, **kwargs)


@router.message(F.text == BTN_INVENTORY_REPORT)
async def inventory_report(
  message: Message, session, state: FSMContext, db_user: User
) -> None:
  await state.clear()
  if db_user.supplier_id is None:
    await message.answer("⛔ Ҳисобингиз етказиб берувчига боғланмаган.")
    return

  context_service = SupplierContextService(session)
  try:
    branch = await context_service.require_branch_context(db_user)
  except SupplierContextError as exc:
    await message.answer(f"⛔ {exc}")
    return

  inventory_service = InventoryService(session)
  summary = await inventory_service.get_supplier_summary(
    db_user.supplier_id, branch.branch_id
  )

  last_update = summary["last_update"]
  last_update_str = (
    last_update.strftime("%Y-%m-%d %H:%M") if last_update else LABEL_NOT_AVAILABLE
  )

  text = (
    "📊 Инвентар ҳисоботи\n\n"
    f"📍 Филиал: {branch.branch_name}\n"
    f"💊 Жами дорилар: {summary['total_medicines']}\n"
    f"📦 Жами қолдиқ: {format_quantity(summary['total_stock'])}\n"
    f"🕐 Охирги янгиланиш: {last_update_str}"
  )
  await message.answer(text)


@router.message(F.text == BTN_BRANCH_REPORT)
async def branch_report(
  message: Message, session, state: FSMContext, db_user: User
) -> None:
  await state.clear()
  if db_user.supplier_id is None:
    await message.answer("⛔ Ҳисобингиз етказиб берувчига боғланмаган.")
    return

  context_service = SupplierContextService(session)
  try:
    branch = await context_service.require_branch_context(db_user)
  except SupplierContextError as exc:
    await message.answer(f"⛔ {exc}")
    return

  inventory_service = InventoryService(session)
  report = await inventory_service.get_branch_report(
    db_user.supplier_id, branch.branch_id
  )

  if not report:
    await message.answer("Инвентар маълумотлари топилмади.")
    return

  lines: list[str] = ["📍 Филиал ҳисоботи\n"]
  for branch_name, items in report:
    lines.append(f"\n📍 {branch_name}")
    for medicine_name, quantity in items:
      lines.append(f"  • {medicine_name} — {format_quantity(quantity)}")

  await _send_long_text(message, lines)


@router.message(F.text == BTN_DOWNLOAD_EXCEL)
async def download_excel(
  message: Message, session, state: FSMContext, db_user: User
) -> None:
  await state.clear()
  if db_user.supplier_id is None:
    await message.answer("⛔ Ҳисобингиз етказиб берувчига боғланмаган.")
    return

  context_service = SupplierContextService(session)
  try:
    branch = await context_service.require_branch_context(db_user)
  except SupplierContextError as exc:
    await message.answer(f"⛔ {exc}")
    return

  await message.answer("⏳ Excel ҳисобот тайёрланмоқда...")

  file_path: str | None = None
  inventory_repo = InventoryRepository(session)
  export_service = ExcelExportService(inventory_repo)

  try:
    file_path, row_count = await export_service.generate_supplier_report(
      db_user.supplier_id, branch.branch_id
    )

    if row_count == 0:
      await message.answer("📭 Бу филиалда инвентар маълумотлари топилмади.")
      return

    safe_branch = "".join(
      ch if ch.isalnum() else "_" for ch in branch.branch_name
    )
    file = FSInputFile(
      file_path,
      filename=f"inventar_{safe_branch}_{datetime.now().strftime('%Y%m%d')}.xlsx",
    )

    await message.answer_document(
      file,
      caption=f"📥 Инвентар ҳисоботи — {branch.branch_name}",
    )
    logger.info(
      "supplier_export",
      user_id=db_user.id,
      supplier_id=db_user.supplier_id,
      branch_id=branch.branch_id,
      rows=row_count,
    )
  except Exception as exc:
    await message.answer("❌ Экспортда хатолик юз берди.")
    logger.error(
      "supplier_export_failed",
      user_id=db_user.id,
      branch_id=branch.branch_id,
      error=str(exc),
    )
  finally:
    if file_path and os.path.exists(file_path):
      os.remove(file_path)
      parent = os.path.dirname(file_path)
      if os.path.exists(parent):
        os.rmdir(parent)


@router.message(F.text == BTN_SEARCH_MEDICINE)
async def search_medicine_prompt(message: Message, state: FSMContext) -> None:
  await state.set_state(SupplierStates.waiting_search_query)
  await message.answer("🔍 Дори номини киритинг:")


@router.message(StateFilter(SupplierStates.waiting_search_query), F.text)
async def search_medicine_result(
  message: Message, session, state: FSMContext, db_user: User
) -> None:
  await state.clear()

  if db_user.supplier_id is None:
    await message.answer("⛔ Ҳисобингиз етказиб берувчига боғланмаган.")
    return

  context_service = SupplierContextService(session)
  try:
    branch = await context_service.require_branch_context(db_user)
  except SupplierContextError as exc:
    await message.answer(f"⛔ {exc}", reply_markup=supplier_menu_keyboard())
    return

  query = message.text.strip() if message.text else ""
  if not query:
    await message.answer(
      "Дори номини киритинг.",
      reply_markup=supplier_menu_keyboard(),
    )
    return

  inventory_service = InventoryService(session)
  results = await inventory_service.search_medicine(
    db_user.supplier_id, branch.branch_id, query
  )

  if not results:
    await message.answer(
      f"«{query}» учун инвентар топилмади.",
      reply_markup=supplier_menu_keyboard(),
    )
    return

  lines = [f"🔍 «{query}» натижалари:"]
  for medicine_name, branch_quantities in results:
    lines.append(f"\n💊 {medicine_name}")
    for branch_name, quantity in branch_quantities:
      lines.append(f"  📍 {branch_name} — {format_quantity(quantity)}")

  await _send_long_text(
    message,
    lines,
    reply_markup=supplier_menu_keyboard(),
  )
