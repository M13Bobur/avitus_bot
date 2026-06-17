import os
import tempfile

from aiogram import F, Router
from aiogram.types import Message

from app.bot.filters.role import IsSuperAdmin
from app.bot.keyboards.menus import admin_menu_keyboard, cancel_keyboard
from app.bot.texts import (
  BTN_CANCEL,
  BTN_STATISTICS,
  BTN_SUPPLIERS,
  BTN_UPLOAD_EXCEL,
  LABEL_NOT_AVAILABLE,
)
from app.database.models import User
from app.logging_config import get_logger
from app.services.app_settings import AppSettingsService
from app.services.auth import StatsService
from app.services.inventory import InventoryService, SupplierLowStockAlert
from app.services.management import SupplierManagementService
from app.utils.quantity import format_quantity

logger = get_logger(__name__)

router = Router(name="admin")
router.message.filter(IsSuperAdmin())

_upload_waiting: set[int] = set()


def _format_low_stock_alert(alert: SupplierLowStockAlert) -> str:
  lines = [
    "⚠️ Кам қолдиқ огоҳлантириши",
    "",
    f"Қуйидаги дориларнинг қолдиғи белгиланган чегарадан ({alert.threshold}) кам:",
  ]

  by_branch: dict[str, list[tuple[str, str]]] = {}
  for medicine, branch, quantity in alert.items:
    by_branch.setdefault(branch, []).append((medicine, format_quantity(quantity)))

  for branch, medicines in by_branch.items():
    lines.append(f"\n📍 {branch}")
    for medicine, quantity in medicines:
      lines.append(f"  • {medicine} — {quantity}")

  text = "\n".join(lines)
  if len(text) > 4000:
    text = text[:4000] + "\n... (қисқартилди)"
  return text


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
      await bot.send_message(alert.telegram_id, _format_low_stock_alert(alert))
      sent += 1
    except Exception as exc:
      logger.warning(
        "low_stock_alert_send_failed",
        supplier_id=alert.supplier_id,
        telegram_id=alert.telegram_id,
        error=str(exc),
      )
  return sent


@router.message(F.text == BTN_UPLOAD_EXCEL)
async def upload_excel_prompt(message: Message, session) -> None:
  _upload_waiting.add(message.from_user.id)
  max_upload_mb = await AppSettingsService(session).get_max_upload_size_mb()
  await message.answer(
    "📤 Инвентар маълумотлари билан Excel файл (.xlsx) юборинг.\n"
    f"Максимал ҳажм: {max_upload_mb} MB",
    reply_markup=cancel_keyboard(),
  )


@router.message(F.text == BTN_CANCEL)
async def cancel_action(message: Message) -> None:
  _upload_waiting.discard(message.from_user.id)
  await message.answer("Бекор қилинди.", reply_markup=admin_menu_keyboard())


@router.message(F.document)
async def handle_document(message: Message, session, db_user: User) -> None:
  if message.from_user.id not in _upload_waiting:
    return

  document = message.document
  if document is None:
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
      file_path, file_name, db_user
    )

    _upload_waiting.discard(message.from_user.id)

    notified = await _send_low_stock_alerts(message.bot, alerts)

    await message.answer(
      f"✅ Импорт муваффақиятли якунланди!\n\n"
      f"📊 Қайта ишланган қаторлар: {processed}\n"
      f"⏭ Ўтказиб юборилган қаторлар: {skipped}\n"
      f"🔔 Огоҳлантириш юборилди: {notified} та фирма",
      reply_markup=admin_menu_keyboard(),
    )
    logger.info(
      "admin_upload_success",
      user_id=db_user.id,
      file_name=file_name,
      processed=processed,
      skipped=skipped,
      alerts_sent=notified,
    )
  except Exception as exc:
    _upload_waiting.discard(message.from_user.id)
    await message.answer(
      f"❌ Импортда хатолик: {exc}",
      reply_markup=admin_menu_keyboard(),
    )
    logger.error(
      "admin_upload_failed",
      user_id=db_user.id,
      file_name=file_name,
      error=str(exc),
    )
  finally:
    if os.path.exists(file_path):
      os.remove(file_path)
    if os.path.exists(tmp_dir):
      os.rmdir(tmp_dir)


@router.message(F.text == BTN_STATISTICS)
async def show_statistics(message: Message, session) -> None:
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
async def show_suppliers(message: Message, session) -> None:
  supplier_service = SupplierManagementService(session)
  suppliers = await supplier_service.get_all_suppliers()

  if not suppliers:
    await message.answer("Етказиб берувчилар топилмади.")
    return

  lines = ["🏭 Етказиб берувчилар:\n"]
  for s in suppliers:
    status = "✅ Фаол" if s.is_active else "❌ Нофаол"
    lines.append(f"• {s.name} — {status}")

  await message.answer("\n".join(lines))

