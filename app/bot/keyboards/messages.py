from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.texts import BTN_BACK, BTN_NEXT
from app.repositories.support_message import MessageConversation
from app.utils.telegram import truncate_button_text

MESSAGES_PER_PAGE = 8

MSG_LIST_PAGE_PREFIX = "msg:page:"
MSG_USER_PREFIX = "msg:user:"
MSG_BACK_TO_LIST = "msg:list"


def _conversation_button_label(item: MessageConversation) -> str:
  name = item.user.full_name.strip()
  if len(name) > 24:
    name = name[:23].rstrip() + "…"

  if item.unread_count > 0:
    label = f"🔔 {name} ({item.unread_count})"
  else:
    label = f"👤 {name}"

  return truncate_button_text(label)


def messages_list_keyboard(
  conversations: list[MessageConversation],
  page: int,
) -> InlineKeyboardMarkup:
  start = page * MESSAGES_PER_PAGE
  end = start + MESSAGES_PER_PAGE
  page_items = conversations[start:end]

  rows: list[list[InlineKeyboardButton]] = []
  for item in page_items:
    rows.append(
      [
        InlineKeyboardButton(
          text=_conversation_button_label(item),
          callback_data=f"{MSG_USER_PREFIX}{item.user.id}",
        )
      ]
    )

  nav: list[InlineKeyboardButton] = []
  if page > 0:
    nav.append(
      InlineKeyboardButton(
        text=BTN_BACK,
        callback_data=f"{MSG_LIST_PAGE_PREFIX}{page - 1}",
      )
    )
  if end < len(conversations):
    nav.append(
      InlineKeyboardButton(
        text=BTN_NEXT,
        callback_data=f"{MSG_LIST_PAGE_PREFIX}{page + 1}",
      )
    )
  if nav:
    rows.append(nav)

  return InlineKeyboardMarkup(inline_keyboard=rows)


def message_thread_keyboard(user_id: int) -> InlineKeyboardMarkup:
  return InlineKeyboardMarkup(
    inline_keyboard=[
      [
        InlineKeyboardButton(
          text=BTN_BACK,
          callback_data=MSG_BACK_TO_LIST,
        )
      ]
    ]
  )
