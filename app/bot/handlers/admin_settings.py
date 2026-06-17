from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.filters.role import IsSuperAdmin
from app.bot.keyboards.menus import admin_menu_keyboard, cancel_keyboard
from app.bot.keyboards.settings import (
  SETTINGS_ADMIN_PASSWORD,
  SETTINGS_SUPPLIER_PASSWORD,
  SETTINGS_THRESHOLD,
  SETTINGS_UPLOAD_SIZE,
  settings_menu_keyboard,
)
from app.bot.states.admin_settings import AdminSettingsStates
from app.bot.texts import BTN_CANCEL, BTN_SETTINGS
from app.services.app_settings import AppSettingsService

router = Router(name="admin_settings")
router.message.filter(IsSuperAdmin())
router.callback_query.filter(IsSuperAdmin())


async def _format_settings_text(app_settings: AppSettingsService) -> str:
  summary = await app_settings.get_summary()
  return (
    "⚙ Созламалар\n\n"
    f"🔐 Админ пароли: {summary['admin_password']}\n"
    f"🔐 Етказиб берувчи пароли: {summary['supplier_password']}\n"
    f"🔔 Кам қолдиқ чегараси: {summary['threshold']}\n"
    f"📁 Макс. файл ҳажми: {summary['max_upload_mb']} MB\n\n"
    "Ўзгартириш учун танланг:"
  )


@router.message(F.text == BTN_SETTINGS)
async def show_settings(message: Message, session, state: FSMContext) -> None:
  await state.clear()
  app_settings = AppSettingsService(session)
  text = await _format_settings_text(app_settings)
  await message.answer(text, reply_markup=settings_menu_keyboard())


@router.callback_query(F.data == SETTINGS_ADMIN_PASSWORD)
async def prompt_admin_password(callback: CallbackQuery, state: FSMContext) -> None:
  await state.set_state(AdminSettingsStates.waiting_admin_password)
  await callback.message.answer(
    "🔐 Янги админ паролини киритинг (камида 4 белги):",
    reply_markup=cancel_keyboard(),
  )
  await callback.answer()


@router.callback_query(F.data == SETTINGS_SUPPLIER_PASSWORD)
async def prompt_supplier_password(callback: CallbackQuery, state: FSMContext) -> None:
  await state.set_state(AdminSettingsStates.waiting_supplier_password)
  await callback.message.answer(
    "🔐 Янги етказиб берувчи паролини киритинг (камида 4 белги):",
    reply_markup=cancel_keyboard(),
  )
  await callback.answer()


@router.callback_query(F.data == SETTINGS_THRESHOLD)
async def prompt_threshold(callback: CallbackQuery, state: FSMContext) -> None:
  await state.set_state(AdminSettingsStates.waiting_threshold)
  await callback.message.answer(
    "🔔 Кам қолдиқ чегарасини киритинг (сон):",
    reply_markup=cancel_keyboard(),
  )
  await callback.answer()


@router.callback_query(F.data == SETTINGS_UPLOAD_SIZE)
async def prompt_upload_size(callback: CallbackQuery, state: FSMContext) -> None:
  await state.set_state(AdminSettingsStates.waiting_upload_size)
  await callback.message.answer(
    "📁 Максимал файл ҳажмини MB да киритинг (1–100):",
    reply_markup=cancel_keyboard(),
  )
  await callback.answer()


@router.message(StateFilter(AdminSettingsStates.waiting_admin_password), F.text)
async def save_admin_password(message: Message, session, state: FSMContext) -> None:
  if message.text == BTN_CANCEL:
    await state.clear()
    await message.answer("Бекор қилинди.", reply_markup=admin_menu_keyboard())
    return

  password = message.text.strip()
  app_settings = AppSettingsService(session)

  try:
    await app_settings.set_admin_password(password)
  except ValueError as exc:
    await message.answer(f"❌ {exc}")
    return

  await state.clear()
  text = await _format_settings_text(app_settings)
  await message.answer(
    f"✅ Админ пароли муваффақиятли ўзгартирилди.\n\n{text}",
    reply_markup=settings_menu_keyboard(),
  )


@router.message(StateFilter(AdminSettingsStates.waiting_supplier_password), F.text)
async def save_supplier_password(message: Message, session, state: FSMContext) -> None:
  if message.text == BTN_CANCEL:
    await state.clear()
    await message.answer("Бекор қилинди.", reply_markup=admin_menu_keyboard())
    return

  password = message.text.strip()
  app_settings = AppSettingsService(session)

  try:
    await app_settings.set_supplier_password(password)
  except ValueError as exc:
    await message.answer(f"❌ {exc}")
    return

  await state.clear()
  text = await _format_settings_text(app_settings)
  await message.answer(
    f"✅ Етказиб берувчи пароли муваффақиятли ўзгартирилди.\n\n{text}",
    reply_markup=settings_menu_keyboard(),
  )


@router.message(StateFilter(AdminSettingsStates.waiting_threshold), F.text)
async def save_threshold(message: Message, session, state: FSMContext) -> None:
  if message.text == BTN_CANCEL:
    await state.clear()
    await message.answer("Бекор қилинди.", reply_markup=admin_menu_keyboard())
    return

  try:
    threshold = int(message.text.strip())
    if threshold < 0:
      raise ValueError
  except ValueError:
    await message.answer("Нотўғри қиймат. Манфий бўлмаган сон киритинг.")
    return

  app_settings = AppSettingsService(session)
  await app_settings.set_low_stock_threshold(threshold)
  await state.clear()

  text = await _format_settings_text(app_settings)
  await message.answer(
    f"✅ Кам қолдиқ чегараси {threshold} га ўзгартирилди.\n\n{text}",
    reply_markup=settings_menu_keyboard(),
  )


@router.message(StateFilter(AdminSettingsStates.waiting_upload_size), F.text)
async def save_upload_size(message: Message, session, state: FSMContext) -> None:
  if message.text == BTN_CANCEL:
    await state.clear()
    await message.answer("Бекор қилинди.", reply_markup=admin_menu_keyboard())
    return

  app_settings = AppSettingsService(session)
  try:
    size_mb = int(message.text.strip())
    await app_settings.set_max_upload_size_mb(size_mb)
  except ValueError as exc:
    if "Ҳажм" in str(exc):
      await message.answer(f"❌ {exc}")
    else:
      await message.answer("Нотўғри қиймат. 1 дан 100 гача сон киритинг.")
    return

  await state.clear()
  text = await _format_settings_text(app_settings)
  await message.answer(
    f"✅ Макс. файл ҳажми {size_mb} MB га ўзгартирилди.\n\n{text}",
    reply_markup=settings_menu_keyboard(),
  )
