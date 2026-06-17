from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.filters.role import IsSuperAdmin
from app.bot.keyboards.menus import admin_menu_keyboard, cancel_keyboard
from app.bot.keyboards.users import (
  USERS_DELETE_CONFIRM_PREFIX,
  USERS_DELETE_PREFIX,
  USERS_PAGE_PREFIX,
  USERS_SEARCH,
  USERS_SEARCH_PAGE_PREFIX,
  USERS_VIEW_PREFIX,
  role_label,
  user_delete_confirm_keyboard,
  user_detail_keyboard,
  users_list_keyboard,
)
from app.bot.states.admin_users import AdminUsersStates
from app.bot.texts import BTN_CANCEL, BTN_USERS
from app.database.models import User, UserRole
from app.logging_config import get_logger
from app.services.management import UserManagementService

logger = get_logger(__name__)

router = Router(name="admin_users")
router.message.filter(IsSuperAdmin())
router.callback_query.filter(IsSuperAdmin())


def _role_name(role: str) -> str:
  if role == UserRole.SUPER_ADMIN.value:
    return "Админ"
  if role == UserRole.SUPPLIER.value:
    return "Етказиб берувчи"
  return role


def _list_text(total: int, *, query: str | None = None) -> str:
  if query is not None:
    if total == 0:
      return f"🔍 «{query}» бўйича ҳеч нарса топилмади."
    return f"🔍 «{query}» бўйича топилди: {total} та\n\nКўриш ёки ўчириш учун танланг:"
  if total == 0:
    return "👤 Фойдаланувчилар топилмади."
  return f"👤 Фойдаланувчилар (жами: {total})\n\nКўриш ёки ўчириш учун танланг:"


def _detail_text(user: User) -> str:
  firm = user.supplier.name if user.supplier is not None else "—"
  phone = user.phone or "—"
  return (
    f"{role_label(user.role)} {user.full_name}\n\n"
    f"🆔 Telegram ID: {user.telegram_id}\n"
    f"📱 Телефон: {phone}\n"
    f"👔 Рол: {_role_name(user.role)}\n"
    f"🏭 Фирма: {firm}"
  )


@router.message(F.text == BTN_USERS)
async def show_users(message: Message, session, state: FSMContext) -> None:
  await state.clear()
  service = UserManagementService(session)
  users = await service.get_all_users()
  await message.answer(
    _list_text(len(users)),
    reply_markup=users_list_keyboard(users, 0),
  )


@router.callback_query(F.data.startswith(USERS_PAGE_PREFIX))
async def users_page(callback: CallbackQuery, session, state: FSMContext) -> None:
  await state.clear()
  page = int(callback.data.removeprefix(USERS_PAGE_PREFIX))
  service = UserManagementService(session)
  users = await service.get_all_users()
  await callback.message.edit_text(
    _list_text(len(users)),
    reply_markup=users_list_keyboard(users, page),
  )
  await callback.answer()


@router.callback_query(F.data.startswith(USERS_SEARCH_PAGE_PREFIX))
async def users_search_page(
  callback: CallbackQuery, session, state: FSMContext
) -> None:
  page = int(callback.data.removeprefix(USERS_SEARCH_PAGE_PREFIX))
  data = await state.get_data()
  query = data.get("search_query")
  service = UserManagementService(session)

  if not query:
    users = await service.get_all_users()
    await callback.message.edit_text(
      _list_text(len(users)),
      reply_markup=users_list_keyboard(users, page),
    )
    await callback.answer()
    return

  users = await service.search_users(query)
  await callback.message.edit_text(
    _list_text(len(users), query=query),
    reply_markup=users_list_keyboard(users, page, search=True),
  )
  await callback.answer()


@router.callback_query(F.data.startswith(USERS_VIEW_PREFIX))
async def view_user(callback: CallbackQuery, session) -> None:
  user_id = int(callback.data.removeprefix(USERS_VIEW_PREFIX))
  service = UserManagementService(session)
  user = await service.get_user(user_id)

  if user is None:
    await callback.answer("Фойдаланувчи топилмади.", show_alert=True)
    return

  await callback.message.edit_text(
    _detail_text(user),
    reply_markup=user_detail_keyboard(user.id),
  )
  await callback.answer()


@router.callback_query(F.data.startswith(USERS_DELETE_PREFIX))
async def delete_user_prompt(
  callback: CallbackQuery, session, db_user: User
) -> None:
  user_id = int(callback.data.removeprefix(USERS_DELETE_PREFIX))

  if db_user.id == user_id:
    await callback.answer(
      "⛔ Ўз ҳисобингизни ўчира олмайсиз.", show_alert=True
    )
    return

  service = UserManagementService(session)
  user = await service.get_user(user_id)
  if user is None:
    await callback.answer("Фойдаланувчи топилмади.", show_alert=True)
    return

  firm = user.supplier.name if user.supplier is not None else "—"
  warning = ""
  if user.role == UserRole.SUPPLIER.value and user.supplier is not None:
    warning = (
      "\n\n♻️ Ўчиргандан сўнг фирма бўшайди ва унга бошқа "
      "одамни тайинлаш мумкин бўлади."
    )

  await callback.message.edit_text(
    f"❓ Қуйидаги фойдаланувчини ўчиришни тасдиқлайсизми?\n\n"
    f"{role_label(user.role)} {user.full_name}\n"
    f"🏭 Фирма: {firm}{warning}",
    reply_markup=user_delete_confirm_keyboard(user.id),
  )
  await callback.answer()


@router.callback_query(F.data.startswith(USERS_DELETE_CONFIRM_PREFIX))
async def delete_user_confirm(
  callback: CallbackQuery, session, db_user: User
) -> None:
  user_id = int(callback.data.removeprefix(USERS_DELETE_CONFIRM_PREFIX))

  if db_user.id == user_id:
    await callback.answer(
      "⛔ Ўз ҳисобингизни ўчира олмайсиз.", show_alert=True
    )
    return

  service = UserManagementService(session)
  deleted = await service.delete_user(user_id)

  if deleted is None:
    await callback.answer("Фойдаланувчи топилмади.", show_alert=True)
  else:
    logger.info(
      "user_deleted",
      admin_id=db_user.id,
      deleted_user_id=user_id,
      telegram_id=deleted.telegram_id,
      supplier_id=deleted.supplier_id,
    )
    await callback.answer("✅ Фойдаланувчи ўчирилди.", show_alert=True)

  users = await service.get_all_users()
  await callback.message.edit_text(
    _list_text(len(users)),
    reply_markup=users_list_keyboard(users, 0),
  )


@router.callback_query(F.data == USERS_SEARCH)
async def search_prompt(callback: CallbackQuery, state: FSMContext) -> None:
  await state.set_state(AdminUsersStates.waiting_search)
  await callback.message.answer(
    "🔍 Исм, телефон рақами ёки фирма номини киритинг:",
    reply_markup=cancel_keyboard(),
  )
  await callback.answer()


@router.message(StateFilter(AdminUsersStates.waiting_search), F.text)
async def search_users(message: Message, session, state: FSMContext) -> None:
  if message.text == BTN_CANCEL:
    await state.clear()
    await message.answer("Бекор қилинди.", reply_markup=admin_menu_keyboard())
    return

  query = message.text.strip()
  if not query:
    await message.answer("Қидириш учун матн киритинг.")
    return

  service = UserManagementService(session)
  users = await service.search_users(query)

  await state.set_state(None)
  await state.update_data(search_query=query)

  await message.answer(
    _list_text(len(users), query=query),
    reply_markup=users_list_keyboard(users, 0, search=True),
  )
