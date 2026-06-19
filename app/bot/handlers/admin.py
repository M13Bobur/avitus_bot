import os
import tempfile

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.filters.role import IsSuperAdmin
from app.bot.keyboards.menus import (
  UPLOAD_BRANCH_PAGE_PREFIX,
  UPLOAD_BRANCH_PREFIX,
  admin_menu_keyboard,
  branches_selection_keyboard,
  branches_selection_text,
  cancel_keyboard,
)
from app.bot.states.admin_upload import AdminUploadStates
from app.bot.texts import BTN_CANCEL, BTN_STATISTICS, BTN_SUPPLIERS, BTN_UPLOAD_EXCEL
from app.database.models import User
from app.logging_config import get_logger
from app.services.app_settings import AppSettingsService
from app.services.inventory import InventoryService, SupplierLowStockAlert
from app.services.management import BranchManagementService
from app.utils.quantity import format_quantity
from app.utils.telegram import split_message_parts

logger = get_logger(__name__)


router = Router(name="admin")
router.message.filter(IsSuperAdmin())
router.callback_query.filter(IsSuperAdmin())


async def _send_low_stock_alerts(
  bot, alerts: list[SupplierLowStockAlert]
) -> int:
  sent = 0
  for alert in alerts:
    if alert.telegram_id is None:
      logger.info(
        "low_stock_alert_skipped_no_telegram",
        supplier_id=alert.supplier_id,
        supplier_name=alert.supplier_name,
        items=len(alert.items),
      )
      continue

    try:
      for part in split_message_parts(
        [
          "⚠️ Кам қолдиқ огоҳлантириши",
          "",
          f"📍 Филиал: {alert.branch_name}",
          f"Қуйидаги дориларнинг қолдиғи белгиланган чегарадан ({alert.threshold}) кам:",
          *[
            f"  • {medicine} — {format_quantity(quantity)}"
            for medicine, _branch, quantity in alert.items
          ],
        ]
      ):
        await bot.send_message(alert.telegram_id, part)
      sent += 1
    except Exception as exc:
      logger.warning(
        "low_stock_alert_send_failed",
        supplier_id=alert.supplier_id,
        telegram_id=alert.telegram_id,
        error=str(exc),
      )
  return sent


async def _prompt_branch_selection(message: Message, session, state: FSMContext) -> None:
  branch_service = BranchManagementService(session)
  branches = await branch_service.get_all_branches()

  if not branches:
    await message.answer(
      "📭 Аввал филиал қўшинг.\n"
      "📍 Филиаллар менюси орқали янги филиал яратинг.",
      reply_markup=admin_menu_keyboard(),
    )
    return

  await state.set_state(AdminUploadStates.waiting_branch)
  await message.answer(
    branches_selection_text(
      branches,
      page=0,
      title="📤 Excel юклаш учун филиални танланг:",
    ),
    reply_markup=branches_selection_keyboard(
      branches,
      page=0,
      item_prefix=UPLOAD_BRANCH_PREFIX,
      page_prefix=UPLOAD_BRANCH_PAGE_PREFIX,
    ),
  )


@router.message(F.text == BTN_UPLOAD_EXCEL)
async def upload_excel_prompt(message: Message, session, state: FSMContext) -> None:
  await state.clear()
  await _prompt_branch_selection(message, session, state)


@router.callback_query(
  StateFilter(AdminUploadStates.waiting_branch),
  F.data.startswith(UPLOAD_BRANCH_PAGE_PREFIX),
)
async def upload_branch_page(callback: CallbackQuery, session, state: FSMContext) -> None:
  page = int(callback.data.replace(UPLOAD_BRANCH_PAGE_PREFIX, ""))
  branch_service = BranchManagementService(session)
  branches = await branch_service.get_all_branches()

  await callback.message.edit_text(
    branches_selection_text(
      branches,
      page=page,
      title="📤 Excel юклаш учун филиални танланг:",
    ),
    reply_markup=branches_selection_keyboard(
      branches,
      page=page,
      item_prefix=UPLOAD_BRANCH_PREFIX,
      page_prefix=UPLOAD_BRANCH_PAGE_PREFIX,
    ),
  )
  await callback.answer()


@router.callback_query(
  StateFilter(AdminUploadStates.waiting_branch),
  F.data.startswith(UPLOAD_BRANCH_PREFIX),
)
async def upload_branch_selected(
  callback: CallbackQuery,
  session,
  state: FSMContext,
) -> None:
  branch_id = int(callback.data.replace(UPLOAD_BRANCH_PREFIX, ""))
  branch_service = BranchManagementService(session)
  branches = await branch_service.get_all_branches()
  branch = next((item for item in branches if item.id == branch_id), None)

  if branch is None:
    await callback.answer("Филиал топилмади", show_alert=True)
    return

  await state.update_data(branch_id=branch_id, branch_name=branch.name)
  await state.set_state(AdminUploadStates.waiting_file)

  app_settings = AppSettingsService(session)
  max_upload_mb = await app_settings.get_max_upload_size_mb()

  await callback.message.edit_reply_markup(reply_markup=None)
  await callback.message.answer(
    f"✅ Танланди: {branch.name}\n\n"
    "📤 Инвентар маълумотлари билан Excel файл (.xlsx) юборинг.\n"
    f"Максимал ҳажм: {max_upload_mb} MB",
    reply_markup=cancel_keyboard(),
  )
  await callback.answer()


@router.message(F.text == BTN_CANCEL)
async def cancel_action(message: Message, state: FSMContext) -> None:
  await state.clear()
  await message.answer("Бекор қилинди.", reply_markup=admin_menu_keyboard())


@router.message(StateFilter(AdminUploadStates.waiting_file), F.document)
async def handle_document(
  message: Message,
  session,
  state: FSMContext,
  db_user: User,
) -> None:
  document = message.document
  if document is None:
    return

  data = await state.get_data()
  branch_id = data.get("branch_id")
  branch_name = data.get("branch_name", "")

  if branch_id is None:
    await state.clear()
    await message.answer(
      "Хатолик юз берди. Қайтадан Excel юклашни бошланг.",
      reply_markup=admin_menu_keyboard(),
    )
    return

  app_settings = AppSettingsService(session)
  max_upload_mb = await app_settings.get_max_upload_size_mb()
  max_upload_bytes = max_upload_mb * 1024 * 1024

  if document.file_size and document.file_size > max_upload_bytes:
    await message.answer(
      f"⛔ Файл жуда катта. Максимал ҳажм: {max_upload_mb} MB."
    )
    return

  file_name = document.file_name or "upload.xlsx"

  await message.answer("⏳ Файл қайта ишланмоқда, илтимос кутинг...")

  tmp_dir = tempfile.mkdtemp()
  file_path = os.path.join(tmp_dir, file_name)

  try:
    bot = message.bot
    file = await bot.get_file(document.file_id)
    await bot.download_file(file.file_path, file_path)

    inventory_service = InventoryService(session)
    processed, skipped, alerts = await inventory_service.import_excel(
      file_path, file_name, db_user, branch_id
    )

    await state.clear()

    notified = await _send_low_stock_alerts(message.bot, alerts)

    await message.answer(
      f"✅ Импорт муваффақиятли якунланди!\n\n"
      f"📍 Филиал: {branch_name}\n"
      f"📊 Қайта ишланган қаторлар: {processed}\n"
      f"⏭ Ўтказиб юборилган қаторлар: {skipped}\n"
      f"🔔 Огоҳлантириш юборилди: {notified} та фирма",
      reply_markup=admin_menu_keyboard(),
    )
    logger.info(
      "admin_upload_success",
      user_id=db_user.id,
      file_name=file_name,
      branch_id=branch_id,
      processed=processed,
      skipped=skipped,
      alerts_sent=notified,
    )
  except Exception as exc:
    await state.clear()
    await message.answer(
      f"❌ Импортда хатолик юз берди. Файл формати ва маълумотларни текширинг.",
      reply_markup=admin_menu_keyboard(),
    )
    logger.error(
      "admin_upload_failed",
      user_id=db_user.id,
      file_name=file_name,
      branch_id=branch_id,
      error=str(exc),
    )
  finally:
    if os.path.exists(file_path):
      os.remove(file_path)
    if os.path.exists(tmp_dir):
      os.rmdir(tmp_dir)


@router.message(StateFilter(AdminUploadStates.waiting_file))
async def handle_upload_invalid(message: Message) -> None:
  await message.answer(
    "📤 Excel файл (.xlsx) юборинг ёки бекор қилиш тугмасини босинг.",
    reply_markup=cancel_keyboard(),
  )


@router.message(F.text == BTN_STATISTICS)
async def show_statistics(message: Message, session, state: FSMContext) -> None:
  await state.clear()
  from app.services.auth import StatsService
  from app.bot.texts import LABEL_NOT_AVAILABLE

  stats_service = StatsService(session)
  stats = await stats_service.get_statistics()

  text = (
    "📈 Тизим статистикаси\n\n"
    f"🏭 Жами етказиб берувчилар: {stats['total_suppliers']}\n"
    f"💊 Жами дорилар: {stats['total_medicines']}\n"
    f"📍 Жами филиаллар: {stats['total_branches']}\n"
    f"📦 Жами инвентар ёзувлари: {stats['total_inventory_records']}\n"
    f"📤 Охирги юклаш: {stats['last_upload_time'] or LABEL_NOT_AVAILABLE}\n"
    f"🕐 Охирги янгиланиш: {stats['last_update_time'] or LABEL_NOT_AVAILABLE}"
  )
  await message.answer(text)


@router.message(F.text == BTN_SUPPLIERS)
async def show_suppliers(message: Message, session, state: FSMContext) -> None:
  await state.clear()
  from app.services.management import SupplierManagementService

  supplier_service = SupplierManagementService(session)
  suppliers = await supplier_service.get_all_suppliers()

  if not suppliers:
    await message.answer("Етказиб берувчилар топилмади.")
    return

  lines = [
    f"🏭 Етказиб берувчи фирмалар (Excelдан) — жами: {len(suppliers)}\n",
    "Бу рўйхат — фирма номлари. Telegram аккаунтлар эмас.",
    "Аккаунтларни кўриш: 👤 Фойдаланувчилар\n",
  ]
  for s in suppliers:
    status = "✅ Фаол" if s.is_active else "❌ Нофаол"
    lines.append(f"• {s.name} — {status}")

  for index, part in enumerate(split_message_parts(lines)):
    if index > 0:
      part = f"🏭 Давоми ({index + 1}):\n\n{part}"
    await message.answer(part)
