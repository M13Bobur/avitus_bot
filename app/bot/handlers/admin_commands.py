from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.filters.role import IsSuperAdmin
from app.database.models import User
from app.services.inventory import InventoryService

router = Router(name="admin_commands")
router.message.filter(IsSuperAdmin())


@router.message(Command("set_threshold"))
async def set_threshold(message: Message, session, db_user: User) -> None:
  parts = message.text.split()
  if len(parts) != 2:
    await message.answer("Фойдаланиш: /set_threshold <сон>")
    return

  try:
    threshold = int(parts[1])
    if threshold < 0:
      raise ValueError("Threshold must be non-negative")
  except ValueError:
    await message.answer("Нотўғри чегара. Манфий бўлмаган сон киритинг.")
    return

  inventory_service = InventoryService(session)
  await inventory_service.set_low_stock_threshold(threshold)

  await message.answer(
    f"✅ Кам қолдиқ чегараси {threshold} га ўзгартирилди.\n"
    "⚙ Созламалар орқали ҳам ўзгартиришингиз мумкин."
  )
