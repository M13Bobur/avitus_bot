from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.filters.role import IsSuperAdmin
from app.bot.keyboards.messages import (
  MSG_BACK_TO_LIST,
  MSG_LIST_PAGE_PREFIX,
  MSG_USER_PREFIX,
  message_thread_keyboard,
  messages_list_keyboard,
)
from app.bot.texts import BTN_MESSAGES
from app.logging_config import get_logger
from app.services.support_message import (
  SupportMessageService,
  format_conversations_list,
  format_user_messages,
)

logger = get_logger(__name__)

router = Router(name="admin_messages")
router.message.filter(IsSuperAdmin())
router.callback_query.filter(IsSuperAdmin())


async def _show_conversations_list(message: Message, session, page: int = 0) -> None:
  service = SupportMessageService(session)
  conversations = await service.get_conversations()
  await message.answer(
    format_conversations_list(conversations),
    reply_markup=messages_list_keyboard(conversations, page),
    parse_mode="HTML",
  )


@router.message(F.text == BTN_MESSAGES)
async def show_messages(message: Message, session, state: FSMContext) -> None:
  await state.clear()
  await _show_conversations_list(message, session)


@router.callback_query(F.data == MSG_BACK_TO_LIST)
async def back_to_messages_list(callback: CallbackQuery, session) -> None:
  service = SupportMessageService(session)
  conversations = await service.get_conversations()
  await callback.message.edit_text(
    format_conversations_list(conversations),
    reply_markup=messages_list_keyboard(conversations, 0),
    parse_mode="HTML",
  )
  await callback.answer()


@router.callback_query(F.data.startswith(MSG_LIST_PAGE_PREFIX))
async def messages_page(callback: CallbackQuery, session) -> None:
  page = int(callback.data.removeprefix(MSG_LIST_PAGE_PREFIX))
  service = SupportMessageService(session)
  conversations = await service.get_conversations()
  await callback.message.edit_text(
    format_conversations_list(conversations),
    reply_markup=messages_list_keyboard(conversations, page),
    parse_mode="HTML",
  )
  await callback.answer()


@router.callback_query(F.data.startswith(MSG_USER_PREFIX))
async def view_user_messages(callback: CallbackQuery, session) -> None:
  user_id = int(callback.data.removeprefix(MSG_USER_PREFIX))
  service = SupportMessageService(session)
  user, messages = await service.get_user_messages(user_id)

  if user is None:
    await callback.answer("Фойдаланувчи топилмади.", show_alert=True)
    return

  parts = format_user_messages(user, messages)
  keyboard = message_thread_keyboard(user_id)

  await callback.message.edit_text(
    parts[0],
    reply_markup=keyboard,
    parse_mode="HTML",
  )

  for part in parts[1:]:
    await callback.message.answer(part, parse_mode="HTML")

  logger.info(
    "admin_viewed_messages",
    admin_telegram_id=callback.from_user.id,
    user_id=user_id,
    message_count=len(messages),
  )
  await callback.answer()
