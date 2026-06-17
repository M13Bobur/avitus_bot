from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.texts import BTN_BACK, BTN_NEXT
from app.database.models import User, UserRole

USERS_PER_PAGE = 6

USERS_PAGE_PREFIX = "usr:page:"
USERS_SEARCH_PAGE_PREFIX = "usr:spage:"
USERS_VIEW_PREFIX = "usr:view:"
USERS_DELETE_PREFIX = "usr:del:"
USERS_DELETE_CONFIRM_PREFIX = "usr:delc:"
USERS_SEARCH = "usr:search"

BTN_USERS_SEARCH = "🔍 Қидириш"
BTN_USERS_ALL = "📋 Барча фойдаланувчилар"
BTN_USERS_DELETE = "🗑 Ўчириш"
BTN_USERS_DELETE_CONFIRM = "✅ Ҳа, ўчириш"


FIRM_NAME_MAX_LEN = 20


def role_label(role: str) -> str:
  if role == UserRole.SUPER_ADMIN.value:
    return "👑"
  if role == UserRole.SUPPLIER.value:
    return "🏭"
  return "👤"


def _shorten_firm_name(name: str) -> str:
  name = name.strip()
  if len(name) <= FIRM_NAME_MAX_LEN:
    return name
  return name[:FIRM_NAME_MAX_LEN].rstrip() + "…"


def user_button_label(user: User) -> str:
  if user.role == UserRole.SUPER_ADMIN.value:
    return f"👑 {user.full_name} — Админ"
  if user.supplier is not None:
    return f"{user.full_name} — {_shorten_firm_name(user.supplier.name)}"
  return f"{user.full_name} — —"


def users_list_keyboard(
  users: list[User],
  page: int,
  *,
  search: bool = False,
) -> InlineKeyboardMarkup:
  start = page * USERS_PER_PAGE
  end = start + USERS_PER_PAGE
  page_users = users[start:end]

  rows: list[list[InlineKeyboardButton]] = []
  for user in page_users:
    rows.append(
      [
        InlineKeyboardButton(
          text=user_button_label(user),
          callback_data=f"{USERS_VIEW_PREFIX}{user.id}",
        )
      ]
    )

  page_prefix = USERS_SEARCH_PAGE_PREFIX if search else USERS_PAGE_PREFIX
  nav: list[InlineKeyboardButton] = []
  if page > 0:
    nav.append(
      InlineKeyboardButton(text=BTN_BACK, callback_data=f"{page_prefix}{page - 1}")
    )
  if end < len(users):
    nav.append(
      InlineKeyboardButton(text=BTN_NEXT, callback_data=f"{page_prefix}{page + 1}")
    )
  if nav:
    rows.append(nav)

  if search:
    rows.append(
      [InlineKeyboardButton(text=BTN_USERS_ALL, callback_data=f"{USERS_PAGE_PREFIX}0")]
    )
  else:
    rows.append(
      [InlineKeyboardButton(text=BTN_USERS_SEARCH, callback_data=USERS_SEARCH)]
    )

  return InlineKeyboardMarkup(inline_keyboard=rows)


def user_detail_keyboard(user_id: int) -> InlineKeyboardMarkup:
  return InlineKeyboardMarkup(
    inline_keyboard=[
      [
        InlineKeyboardButton(
          text=BTN_USERS_DELETE,
          callback_data=f"{USERS_DELETE_PREFIX}{user_id}",
        )
      ],
      [
        InlineKeyboardButton(
          text=BTN_BACK,
          callback_data=f"{USERS_PAGE_PREFIX}0",
        )
      ],
    ]
  )


def user_delete_confirm_keyboard(user_id: int) -> InlineKeyboardMarkup:
  return InlineKeyboardMarkup(
    inline_keyboard=[
      [
        InlineKeyboardButton(
          text=BTN_USERS_DELETE_CONFIRM,
          callback_data=f"{USERS_DELETE_CONFIRM_PREFIX}{user_id}",
        )
      ],
      [
        InlineKeyboardButton(
          text=BTN_BACK,
          callback_data=f"{USERS_VIEW_PREFIX}{user_id}",
        )
      ],
    ]
  )
