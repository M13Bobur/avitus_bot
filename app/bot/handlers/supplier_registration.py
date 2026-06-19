from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.menus import (
  REG_BRANCH_PAGE_PREFIX,
  REG_BRANCH_PREFIX,
  REG_PAGE_PREFIX,
  REG_SUPPLIER_PREFIX,
  branches_selection_keyboard,
  branches_selection_text,
  request_phone_keyboard,
  supplier_menu_keyboard,
  suppliers_selection_keyboard,
  suppliers_selection_text,
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
  branches = await registration_service.get_branches()

  if not branches:
    await state.clear()
    await message.answer(
      "📭 Ҳозирча филиаллар рўйхати бўш.\n"
      "Админ филиал қўшгандан кейин /start ни қайта босинг."
    )
    return

  await state.set_state(SupplierRegistrationStates.waiting_branch)
  await message.answer(
    branches_selection_text(branches, page=0, title="📍 Филиални танланг:"),
    reply_markup=branches_selection_keyboard(branches, page=0),
  )


@router.callback_query(
  StateFilter(SupplierRegistrationStates.waiting_branch),
  F.data.startswith(REG_BRANCH_PAGE_PREFIX),
)
async def process_branch_page(
  callback: CallbackQuery,
  state: FSMContext,
  session,
) -> None:
  page = int(callback.data.replace(REG_BRANCH_PAGE_PREFIX, ""))
  registration_service = SupplierRegistrationService(session)
  branches = await registration_service.get_branches()

  await callback.message.edit_text(
    branches_selection_text(branches, page=page, title="📍 Филиални танланг:"),
    reply_markup=branches_selection_keyboard(branches, page=page),
  )
  await callback.answer()


@router.callback_query(
  StateFilter(SupplierRegistrationStates.waiting_branch),
  F.data.startswith(REG_BRANCH_PREFIX),
)
async def process_branch_selection(
  callback: CallbackQuery,
  state: FSMContext,
  session,
) -> None:
  branch_id = int(callback.data.replace(REG_BRANCH_PREFIX, ""))

  from app.repositories.branch import BranchRepository

  branch_repo = BranchRepository(session)
  branch = await branch_repo.get_by_id(branch_id)

  if branch is None:
    await callback.answer("Филиал топилмади", show_alert=True)
    return

  registration_service = SupplierRegistrationService(session)
  suppliers = await registration_service.get_available_suppliers(branch_id)
  busy_supplier_ids = await registration_service.get_busy_supplier_ids(branch_id)

  if not suppliers:
    await callback.answer(
      "Бу филиалда ҳозирча фирмалар йўқ. Админ Excel юклагандан кейин қайта урининг.",
      show_alert=True,
    )
    return

  await state.update_data(branch_id=branch_id, branch_name=branch.name)
  await state.set_state(SupplierRegistrationStates.waiting_company)

  await callback.message.edit_reply_markup(reply_markup=None)
  await callback.message.answer(
    f"✅ Филиал: {branch.name}\n\n"
    f"{suppliers_selection_text(suppliers, page=0, busy_supplier_ids=busy_supplier_ids)}",
    reply_markup=suppliers_selection_keyboard(suppliers, page=0),
  )
  await callback.answer()


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
  data = await state.get_data()
  branch_id = data.get("branch_id")

  if branch_id is None:
    await callback.answer("Хатолик юз берди. /start билан қайта бошланг.", show_alert=True)
    return

  registration_service = SupplierRegistrationService(session)
  suppliers = await registration_service.get_available_suppliers(branch_id)
  busy_supplier_ids = await registration_service.get_busy_supplier_ids(branch_id)

  await callback.message.edit_text(
    suppliers_selection_text(
      suppliers, page=page, busy_supplier_ids=busy_supplier_ids
    ),
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
  data = await state.get_data()
  branch_id = data.get("branch_id")

  if branch_id is None:
    await callback.answer("Хатолик юз берди. /start билан қайта бошланг.", show_alert=True)
    return

  from app.repositories.supplier import SupplierRepository

  supplier_repo = SupplierRepository(session)
  supplier = await supplier_repo.get_by_id(supplier_id)

  if supplier is None:
    await callback.answer("Фирма топилмади", show_alert=True)
    return

  registration_service = SupplierRegistrationService(session)
  if supplier_id in await registration_service.get_busy_supplier_ids(branch_id):
    await callback.answer("Бу фирма бу филиалда аллақачон рўйхатдан ўтган", show_alert=True)
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
  branch_id = data.get("branch_id")
  branch_name = data.get("branch_name", "")

  if supplier_id is None or branch_id is None:
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
      branch_id=branch_id,
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
    f"📍 Филиал: {branch_name}\n"
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
