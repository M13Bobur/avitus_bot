from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.filters.role import IsSuperAdmin
from app.bot.keyboards.menus import (
  BRANCH_ADD_CALLBACK,
  BRANCH_ADMIN_PAGE_PREFIX,
  BRANCH_DELETE_CONFIRM_PREFIX,
  BRANCH_DELETE_PREFIX,
  BRANCH_LIST_CALLBACK,
  admin_menu_keyboard,
  branch_delete_confirm_keyboard,
  branches_admin_keyboard,
  branches_list_text,
  cancel_keyboard,
)
from app.bot.states.admin_branches import AdminBranchesStates
from app.bot.texts import BTN_BRANCHES, BTN_CANCEL
from app.logging_config import get_logger
from app.services.management import BranchManagementError, BranchManagementService

logger = get_logger(__name__)

router = Router(name="admin_branches")
router.message.filter(IsSuperAdmin())
router.callback_query.filter(IsSuperAdmin())


async def _show_branches_list(
  message: Message,
  session,
  *,
  page: int = 0,
  edit: bool = False,
) -> None:
  branch_service = BranchManagementService(session)
  branches = await branch_service.get_all_branches()
  text = branches_list_text(branches, page=page)
  keyboard = branches_admin_keyboard(branches, page=page)

  if edit:
    await message.edit_text(text, reply_markup=keyboard)
  else:
    await message.answer(text, reply_markup=keyboard)


@router.message(F.text == BTN_BRANCHES)
async def show_branches(message: Message, session, state: FSMContext) -> None:
  await state.clear()
  await _show_branches_list(message, session)


@router.callback_query(F.data.startswith(BRANCH_ADMIN_PAGE_PREFIX))
async def branches_admin_page(callback: CallbackQuery, session) -> None:
  try:
    page = int(callback.data.replace(BRANCH_ADMIN_PAGE_PREFIX, ""))
  except ValueError:
    await callback.answer("Хатолик", show_alert=True)
    return

  await _show_branches_list(callback.message, session, page=page, edit=True)
  await callback.answer()


@router.callback_query(F.data == BRANCH_LIST_CALLBACK)
async def back_to_branches_list(callback: CallbackQuery, session, state: FSMContext) -> None:
  await state.clear()
  await _show_branches_list(callback.message, session, edit=True)
  await callback.answer()


@router.callback_query(F.data == BRANCH_ADD_CALLBACK)
async def prompt_add_branch(callback: CallbackQuery, state: FSMContext) -> None:
  await state.set_state(AdminBranchesStates.waiting_branch_name)
  await callback.message.answer(
    "📍 Янги филиал номини киритинг:",
    reply_markup=cancel_keyboard(),
  )
  await callback.answer()


@router.callback_query(F.data.startswith(BRANCH_DELETE_PREFIX))
async def prompt_delete_branch(callback: CallbackQuery, session) -> None:
  try:
    branch_id = int(callback.data.replace(BRANCH_DELETE_PREFIX, ""))
  except ValueError:
    await callback.answer("Хатолик", show_alert=True)
    return
  branch_service = BranchManagementService(session)
  branch = await branch_service.get_branch(branch_id)

  if branch is None:
    await callback.answer("Филиал топилмади.", show_alert=True)
    return

  stats = await branch_service.get_branch_stats(branch_id)
  await callback.message.edit_text(
    "❓ Филиални ўчиришни тасдиқлайсизми?\n\n"
    f"📍 {branch.name}\n"
    f"📦 Инвентар ёзувлари: {stats['inventory_records']}\n"
    f"👤 Етказиб берувчилар: {stats['supplier_users']}\n\n"
    "⚠️ Филиал ўчирилса, ундаги инвентар маълумотлари ҳам ўчирилади.",
    reply_markup=branch_delete_confirm_keyboard(branch_id),
  )
  await callback.answer()


@router.callback_query(F.data.startswith(BRANCH_DELETE_CONFIRM_PREFIX))
async def confirm_delete_branch(callback: CallbackQuery, session, state: FSMContext) -> None:
  try:
    branch_id = int(callback.data.replace(BRANCH_DELETE_CONFIRM_PREFIX, ""))
  except ValueError:
    await callback.answer("Хатолик", show_alert=True)
    return
  branch_service = BranchManagementService(session)

  try:
    branch, stats = await branch_service.delete_branch(branch_id)
  except BranchManagementError as exc:
    await callback.answer(str(exc), show_alert=True)
    return
  except Exception as exc:
    logger.error("branch_delete_failed", branch_id=branch_id, error=str(exc))
    await callback.answer(
      "Филиални ўчириб бўлмади. Қайта уриниб кўринг.",
      show_alert=True,
    )
    return

  await state.clear()
  logger.info(
    "branch_deleted",
    branch_id=branch.id,
    name=branch.name,
    inventory_records=stats["inventory_records"],
    supplier_users=stats["supplier_users"],
  )

  await _show_branches_list(callback.message, session, edit=True)
  await callback.answer("✅ Филиал ўчирилди")


@router.message(StateFilter(AdminBranchesStates.waiting_branch_name), F.text)
async def save_branch(message: Message, session, state: FSMContext) -> None:
  if message.text == BTN_CANCEL:
    await state.clear()
    await message.answer("Бекор қилинди.", reply_markup=admin_menu_keyboard())
    return

  branch_service = BranchManagementService(session)
  name = message.text.strip() if message.text else ""

  try:
    branch = await branch_service.create_branch(name)
  except BranchManagementError as exc:
    await message.answer(f"❌ {exc}", reply_markup=cancel_keyboard())
    return

  await state.clear()
  logger.info("branch_created", branch_id=branch.id, name=branch.name)
  await message.answer(
    f"✅ Филиал қўшилди: {branch.name}",
    reply_markup=admin_menu_keyboard(),
  )
  await _show_branches_list(message, session)


@router.message(StateFilter(AdminBranchesStates.waiting_branch_name))
async def save_branch_invalid(message: Message) -> None:
  await message.answer(
    "📍 Филиал номини матн сифатида киритинг.",
    reply_markup=cancel_keyboard(),
  )
