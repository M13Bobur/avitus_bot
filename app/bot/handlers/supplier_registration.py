from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.menus import (
  REG_PAGE_PREFIX,
  REG_SUPPLIER_PREFIX,
  request_phone_keyboard,
  supplier_menu_keyboard,
  suppliers_selection_keyboard,
)
from app.bot.states.registration import SupplierRegistrationStates
from app.database.models import User, UserRole
from app.logging_config import get_logger
from app.services.app_settings import AppSettingsService
from app.services.supplier_registration import (
  SupplierRegistrationError,
  SupplierRegistrationService,
)

logger = get_logger(__name__)

router = Router(name="supplier_registration")


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, db_user: User | None = None) -> None:
  if db_user is not None:
    await state.clear()
    if db_user.role == UserRole.SUPER_ADMIN.value:
      from app.bot.keyboards.menus import admin_menu_keyboard

      await message.answer(
        "👋 Администратор, хуш келибсиз!\n\nМенюдан танланг.",
        reply_markup=admin_menu_keyboard(),
      )
      return

    if db_user.role == UserRole.SUPPLIER.value:
      await message.answer(
        "👋 Хуш келибсиз!\n\nМенюдан танланг.",
        reply_markup=supplier_menu_keyboard(),
      )
      return

    await message.answer("⛔ Номаълум рол. Администратор билан боғланинг.")
    return

  await state.set_state(SupplierRegistrationStates.waiting_password)
  await message.answer(
    "🔐 Ботдан фойдаланиш учун паролни киритинг:\n"
    "(админ ёки етказиб берувчи пароли)",
    reply_markup=None,
  )


@router.message(StateFilter(SupplierRegistrationStates.waiting_password), F.text)
async def process_password(
  message: Message,
  state: FSMContext,
  session,
) -> None:
  if message.from_user is None:
    return

  password = message.text.strip() if message.text else ""
  app_settings = AppSettingsService(session)
  admin_password = await app_settings.get_admin_password()
  supplier_password = await app_settings.get_supplier_password()

  if password == admin_password:
    await state.set_state(SupplierRegistrationStates.waiting_admin_phone)
    await message.answer(
      "✅ Парол тўғри!\n\n"
      "📱 Давом этиш учун телефон рақамингизни улашинг:",
      reply_markup=request_phone_keyboard(),
    )
    return

  if password != supplier_password:
    await message.answer("❌ Нотўғри парол. Қайта уриниб кўринг:")
    return

  registration_service = SupplierRegistrationService(session)
  suppliers = await registration_service.get_available_suppliers()

  if not suppliers:
    await state.clear()
    await message.answer(
      "📭 Ҳозирча фирмалар рўйхати бўш.\n"
      "Админ Excel юклагандан кейин /start ни қайта босинг."
    )
    return

  await state.set_state(SupplierRegistrationStates.waiting_company)
  await message.answer(
    "🏭 Фирмани танланг:",
    reply_markup=suppliers_selection_keyboard(suppliers, page=0),
  )


@router.callback_query(
  StateFilter(SupplierRegistrationStates.waiting_company),
  F.data.startswith(REG_PAGE_PREFIX),
)
async def process_company_page(
  callback: CallbackQuery,
  state: FSMContext,
  session,
) -> None:
  page = int(callback.data.replace(REG_PAGE_PREFIX, ""))
  registration_service = SupplierRegistrationService(session)
  suppliers = await registration_service.get_available_suppliers()

  await callback.message.edit_reply_markup(
    reply_markup=suppliers_selection_keyboard(suppliers, page=page),
  )
  await callback.answer()


@router.callback_query(
  StateFilter(SupplierRegistrationStates.waiting_company),
  F.data.startswith(REG_SUPPLIER_PREFIX),
)
async def process_company_selection(
  callback: CallbackQuery,
  state: FSMContext,
  session,
) -> None:
  supplier_id = int(callback.data.replace(REG_SUPPLIER_PREFIX, ""))

  from app.repositories.supplier import SupplierRepository

  supplier_repo = SupplierRepository(session)
  supplier = await supplier_repo.get_by_id(supplier_id)

  if supplier is None:
    await callback.answer("Фирма топилмади", show_alert=True)
    return

  if supplier.telegram_id is not None:
    await callback.answer("Бу фирма аллақачон рўйхатдан ўтган", show_alert=True)
    return

  await state.update_data(supplier_id=supplier_id, supplier_name=supplier.name)
  await state.set_state(SupplierRegistrationStates.waiting_phone)

  await callback.message.edit_reply_markup(reply_markup=None)
  await callback.message.answer(
    f"✅ Танланди: {supplier.name}\n\n"
    "📱 Давом этиш учун телефон рақамингизни улашинг:",
    reply_markup=request_phone_keyboard(),
  )
  await callback.answer()


@router.message(
  StateFilter(SupplierRegistrationStates.waiting_admin_phone),
  F.contact,
)
async def process_admin_phone_contact(
  message: Message,
  state: FSMContext,
  session,
) -> None:
  contact = message.contact
  if contact is None or message.from_user is None:
    return

  if contact.user_id != message.from_user.id:
    await message.answer(
      "⛔ Фақат ўз телефон рақамингизни улашинг.",
      reply_markup=request_phone_keyboard(),
    )
    return

  phone = contact.phone_number
  if not phone:
    await message.answer(
      "⛔ Телефон рақам олинмади. Қайта уриниб кўринг.",
      reply_markup=request_phone_keyboard(),
    )
    return

  registration_service = SupplierRegistrationService(session)
  full_name = message.from_user.full_name or "Админ"

  try:
    await registration_service.register_admin_user(
      telegram_id=message.from_user.id,
      full_name=full_name,
      phone=phone,
    )
  except SupplierRegistrationError as exc:
    await state.clear()
    await message.answer(f"❌ {exc}")
    return

  await state.clear()
  from app.bot.keyboards.menus import admin_menu_keyboard

  logger.info("admin_registered", telegram_id=message.from_user.id, phone=phone)
  await message.answer(
    "✅ Сиз админ сифатида рўйхатдан ўтдингиз!\n\nМенюдан танланг.",
    reply_markup=admin_menu_keyboard(),
  )


@router.message(StateFilter(SupplierRegistrationStates.waiting_admin_phone))
async def process_admin_phone_invalid(message: Message) -> None:
  await message.answer(
    "📱 Телефон рақамини улашиш тугмасини босинг.",
    reply_markup=request_phone_keyboard(),
  )


@router.message(
  StateFilter(SupplierRegistrationStates.waiting_phone),
  F.contact,
)
async def process_phone_contact(
  message: Message,
  state: FSMContext,
  session,
) -> None:
  contact = message.contact
  if contact is None or message.from_user is None:
    return

  if contact.user_id != message.from_user.id:
    await message.answer(
      "⛔ Фақат ўз телефон рақамингизни улашинг.",
      reply_markup=request_phone_keyboard(),
    )
    return

  phone = contact.phone_number
  if not phone:
    await message.answer(
      "⛔ Телефон рақам олинмади. Қайта уриниб кўринг.",
      reply_markup=request_phone_keyboard(),
    )
    return

  data = await state.get_data()
  supplier_id = data.get("supplier_id")
  supplier_name = data.get("supplier_name", "")

  if supplier_id is None:
    await state.clear()
    await message.answer("Хатолик юз берди. /start билан қайта бошланг.")
    return

  registration_service = SupplierRegistrationService(session)
  full_name = message.from_user.full_name or "Етказиб берувчи"

  try:
    await registration_service.register_supplier_user(
      telegram_id=message.from_user.id,
      full_name=full_name,
      phone=phone,
      supplier_id=supplier_id,
    )
  except SupplierRegistrationError as exc:
    await state.clear()
    await message.answer(f"❌ {exc}")
    return

  await state.clear()
  logger.info(
    "supplier_registered",
    telegram_id=message.from_user.id,
    supplier_id=supplier_id,
    phone=phone,
  )

  await message.answer(
    f"✅ Рўйхатдан ўтиш муваффақиятли!\n\n"
    f"🏭 Фирма: {supplier_name}\n"
    f"📱 Телефон: {phone}\n\n"
    "Энди инвентар маълумотларини кўришингиз мумкин.",
    reply_markup=supplier_menu_keyboard(),
  )


@router.message(StateFilter(SupplierRegistrationStates.waiting_phone))
async def process_phone_invalid(message: Message) -> None:
  await message.answer(
    "📱 Телефон рақамини улашиш тугмасини босинг.",
    reply_markup=request_phone_keyboard(),
  )
