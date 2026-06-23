from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.bot.texts import (
  BTN_ADD_BRANCH,
  BTN_BACK,
  BTN_BRANCH_DELETE_CONFIRM,
  BTN_BRANCH_REPORT,
  BTN_BRANCHES,
  BTN_CANCEL,
  BTN_CONTACT_ADMIN,
  BTN_DOWNLOAD_EXCEL,
  BTN_INVENTORY_REPORT,
  BTN_MESSAGES,
  BTN_NEXT,
  BTN_SEARCH_MEDICINE,
  BTN_SETTINGS,
  BTN_SHARE_PHONE,
  BTN_STATISTICS,
  BTN_SUPPLIERS,
  BTN_UPLOAD_EXCEL,
  BTN_USERS,
  LABEL_SUPPLIER_BUSY,
)
from app.database.models import Branch, Supplier

BRANCHES_PER_PAGE = 20
BRANCHES_BUTTONS_PER_ROW = 5
REG_BRANCH_PREFIX = "reg_br:"
REG_BRANCH_PAGE_PREFIX = "reg_bpage:"
UPLOAD_BRANCH_PREFIX = "upl_br:"
UPLOAD_BRANCH_PAGE_PREFIX = "upl_bpage:"
BRANCH_ADD_CALLBACK = "branch:add"
BRANCH_DELETE_PREFIX = "branch:del:"
BRANCH_DELETE_CONFIRM_PREFIX = "branch:delc:"
BRANCH_LIST_CALLBACK = "branch:list"
BRANCH_ADMIN_PAGE_PREFIX = "branch:apage:"

SUPPLIERS_PER_PAGE = 20
REG_SUPPLIER_PREFIX = "reg_sup:"
REG_PAGE_PREFIX = "reg_page:"
SUPPLIERS_BUTTONS_PER_ROW = 5


def _build_paginated_number_keyboard(
  items: list,
  page: int,
  *,
  per_page: int,
  buttons_per_row: int,
  item_prefix: str,
  page_prefix: str,
  get_item_id,
) -> InlineKeyboardMarkup:
  builder = InlineKeyboardBuilder()
  start = page * per_page
  end = start + per_page
  page_items = items[start:end]

  for index, item in enumerate(page_items, start=1):
    builder.button(
      text=str(index),
      callback_data=f"{item_prefix}{get_item_id(item)}",
    )

  row_sizes: list[int] = []
  for row_start in range(0, len(page_items), buttons_per_row):
    row_sizes.append(min(buttons_per_row, len(page_items) - row_start))

  nav_buttons: list = []
  if page > 0:
    nav_buttons.append((BTN_BACK, f"{page_prefix}{page - 1}"))
  if end < len(items):
    nav_buttons.append((BTN_NEXT, f"{page_prefix}{page + 1}"))

  for text, callback_data in nav_buttons:
    builder.button(text=text, callback_data=callback_data)

  if nav_buttons:
    row_sizes.append(len(nav_buttons))

  if row_sizes:
    builder.adjust(*row_sizes)

  return builder.as_markup()


def branches_selection_text(
  branches: list[Branch],
  page: int = 0,
  *,
  title: str = "📍 Филиални танланг:",
) -> str:
  start = page * BRANCHES_PER_PAGE
  end = start + BRANCHES_PER_PAGE
  page_branches = branches[start:end]
  total_pages = max(1, (len(branches) + BRANCHES_PER_PAGE - 1) // BRANCHES_PER_PAGE)

  lines = [title]
  if total_pages > 1:
    lines[0] += f" (саҳифа {page + 1}/{total_pages})"
  lines.append("")

  for index, branch in enumerate(page_branches, start=1):
    lines.append(f"{index}. {branch.name}")

  return "\n".join(lines)


def branches_selection_keyboard(
  branches: list[Branch],
  page: int = 0,
  *,
  item_prefix: str = REG_BRANCH_PREFIX,
  page_prefix: str = REG_BRANCH_PAGE_PREFIX,
) -> InlineKeyboardMarkup:
  return _build_paginated_number_keyboard(
    branches,
    page,
    per_page=BRANCHES_PER_PAGE,
    buttons_per_row=BRANCHES_BUTTONS_PER_ROW,
    item_prefix=item_prefix,
    page_prefix=page_prefix,
    get_item_id=lambda branch: branch.id,
  )


def branches_list_text(branches: list[Branch], page: int = 0) -> str:
  if not branches:
    return "📍 Филиаллар рўйхати бўш.\n\nФилиал қўшиш учун тугмани босинг."

  start = page * BRANCHES_PER_PAGE
  end = start + BRANCHES_PER_PAGE
  page_branches = branches[start:end]
  total_pages = max(1, (len(branches) + BRANCHES_PER_PAGE - 1) // BRANCHES_PER_PAGE)

  lines = ["📍 Филиаллар:"]
  if total_pages > 1:
    lines[0] += f" (саҳифа {page + 1}/{total_pages})"
  lines.append("Ўчириш учун рақамли тугмани босинг:\n")

  for index, branch in enumerate(page_branches, start=start + 1):
    lines.append(f"{index}. {branch.name}")
  return "\n".join(lines)


def branches_admin_keyboard(branches: list[Branch], page: int = 0) -> InlineKeyboardMarkup:
  start = page * BRANCHES_PER_PAGE
  end = start + BRANCHES_PER_PAGE
  page_branches = branches[start:end]

  rows: list[list[InlineKeyboardButton]] = []
  if page_branches:
    delete_row: list[InlineKeyboardButton] = []
    for index, branch in enumerate(page_branches, start=start + 1):
      delete_row.append(
        InlineKeyboardButton(
          text=f"🗑 {index}",
          callback_data=f"{BRANCH_DELETE_PREFIX}{branch.id}",
        )
      )
      if len(delete_row) == 5:
        rows.append(delete_row)
        delete_row = []
    if delete_row:
      rows.append(delete_row)

  nav: list[InlineKeyboardButton] = []
  if page > 0:
    nav.append(
      InlineKeyboardButton(text=BTN_BACK, callback_data=f"{BRANCH_ADMIN_PAGE_PREFIX}{page - 1}")
    )
  if end < len(branches):
    nav.append(
      InlineKeyboardButton(text=BTN_NEXT, callback_data=f"{BRANCH_ADMIN_PAGE_PREFIX}{page + 1}")
    )
  if nav:
    rows.append(nav)

  rows.append(
    [InlineKeyboardButton(text=BTN_ADD_BRANCH, callback_data=BRANCH_ADD_CALLBACK)]
  )
  return InlineKeyboardMarkup(inline_keyboard=rows)


def branch_delete_confirm_keyboard(branch_id: int) -> InlineKeyboardMarkup:
  return InlineKeyboardMarkup(
    inline_keyboard=[
      [
        InlineKeyboardButton(
          text=BTN_BRANCH_DELETE_CONFIRM,
          callback_data=f"{BRANCH_DELETE_CONFIRM_PREFIX}{branch_id}",
        ),
        InlineKeyboardButton(text=BTN_BACK, callback_data=BRANCH_LIST_CALLBACK),
      ]
    ]
  )


def _supplier_busy_suffix(supplier: Supplier, busy_supplier_ids: set[int]) -> str:
  if supplier.id in busy_supplier_ids:
    return f" ({LABEL_SUPPLIER_BUSY})"
  return ""


def suppliers_selection_text(
  suppliers: list[Supplier],
  page: int = 0,
  *,
  busy_supplier_ids: set[int] | None = None,
) -> str:
  busy_supplier_ids = busy_supplier_ids or set()
  start = page * SUPPLIERS_PER_PAGE
  end = start + SUPPLIERS_PER_PAGE
  page_suppliers = suppliers[start:end]
  total_pages = max(1, (len(suppliers) + SUPPLIERS_PER_PAGE - 1) // SUPPLIERS_PER_PAGE)

  lines = ["🏭 Фирмани танланг:"]
  if total_pages > 1:
    lines[0] += f" (саҳифа {page + 1}/{total_pages})"
  lines.append("")

  for index, supplier in enumerate(page_suppliers, start=1):
    lines.append(
      f"{index}. {supplier.name}{_supplier_busy_suffix(supplier, busy_supplier_ids)}"
    )

  return "\n".join(lines)


def supplier_menu_keyboard() -> ReplyKeyboardMarkup:
  builder = ReplyKeyboardBuilder()
  builder.button(text=BTN_INVENTORY_REPORT)
  builder.button(text=BTN_BRANCH_REPORT)
  builder.button(text=BTN_DOWNLOAD_EXCEL)
  builder.button(text=BTN_SEARCH_MEDICINE)
  builder.button(text=BTN_CONTACT_ADMIN)
  builder.adjust(2, 2, 1)
  return builder.as_markup(resize_keyboard=True)


def admin_menu_keyboard() -> ReplyKeyboardMarkup:
  builder = ReplyKeyboardBuilder()
  builder.button(text=BTN_UPLOAD_EXCEL)
  builder.button(text=BTN_BRANCHES)
  builder.button(text=BTN_STATISTICS)
  builder.button(text=BTN_SUPPLIERS)
  builder.button(text=BTN_USERS)
  builder.button(text=BTN_SETTINGS)
  builder.button(text=BTN_MESSAGES)
  builder.adjust(2, 2, 2, 1)
  return builder.as_markup(resize_keyboard=True)


def cancel_keyboard() -> ReplyKeyboardMarkup:
  builder = ReplyKeyboardBuilder()
  builder.button(text=BTN_CANCEL)
  return builder.as_markup(resize_keyboard=True)


def request_phone_keyboard() -> ReplyKeyboardMarkup:
  builder = ReplyKeyboardBuilder()
  builder.button(text=BTN_SHARE_PHONE, request_contact=True)
  return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def suppliers_selection_keyboard(
  suppliers: list[Supplier],
  page: int = 0,
) -> InlineKeyboardMarkup:
  return _build_paginated_number_keyboard(
    suppliers,
    page,
    per_page=SUPPLIERS_PER_PAGE,
    buttons_per_row=SUPPLIERS_BUTTONS_PER_ROW,
    item_prefix=REG_SUPPLIER_PREFIX,
    page_prefix=REG_PAGE_PREFIX,
    get_item_id=lambda supplier: supplier.id,
  )
