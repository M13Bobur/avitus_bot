from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.bot.texts import (
  BTN_BACK,
  BTN_BRANCH_REPORT,
  BTN_CANCEL,
  BTN_DOWNLOAD_EXCEL,
  BTN_INVENTORY_REPORT,
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
from app.database.models import Supplier

SUPPLIERS_PER_PAGE = 8
REG_SUPPLIER_PREFIX = "reg_sup:"
REG_PAGE_PREFIX = "reg_page:"


def supplier_menu_keyboard() -> ReplyKeyboardMarkup:
  builder = ReplyKeyboardBuilder()
  builder.button(text=BTN_INVENTORY_REPORT)
  builder.button(text=BTN_BRANCH_REPORT)
  builder.button(text=BTN_DOWNLOAD_EXCEL)
  builder.button(text=BTN_SEARCH_MEDICINE)
  builder.adjust(2, 2)
  return builder.as_markup(resize_keyboard=True)


def admin_menu_keyboard() -> ReplyKeyboardMarkup:
  builder = ReplyKeyboardBuilder()
  builder.button(text=BTN_UPLOAD_EXCEL)
  builder.button(text=BTN_STATISTICS)
  builder.button(text=BTN_SUPPLIERS)
  builder.button(text=BTN_USERS)
  builder.button(text=BTN_SETTINGS)
  builder.adjust(2, 2, 1)
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
  builder = InlineKeyboardBuilder()
  start = page * SUPPLIERS_PER_PAGE
  end = start + SUPPLIERS_PER_PAGE
  page_suppliers = suppliers[start:end]

  for supplier in page_suppliers:
    label = supplier.name
    if supplier.telegram_id is not None:
      label = f"{supplier.name} ({LABEL_SUPPLIER_BUSY})"
    builder.button(
      text=label,
      callback_data=f"{REG_SUPPLIER_PREFIX}{supplier.id}",
    )

  builder.adjust(1)

  nav_buttons: list = []
  if page > 0:
    nav_buttons.append((BTN_BACK, f"{REG_PAGE_PREFIX}{page - 1}"))
  if end < len(suppliers):
    nav_buttons.append((BTN_NEXT, f"{REG_PAGE_PREFIX}{page + 1}"))

  for text, callback_data in nav_buttons:
    builder.button(text=text, callback_data=callback_data)

  if nav_buttons:
    builder.adjust(len(nav_buttons))

  return builder.as_markup()
