from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

SETTINGS_ADMIN_PASSWORD = "settings:admin_password"
SETTINGS_SUPPLIER_PASSWORD = "settings:supplier_password"
SETTINGS_THRESHOLD = "settings:threshold"
SETTINGS_UPLOAD_SIZE = "settings:upload_size"


def settings_menu_keyboard() -> InlineKeyboardMarkup:
  builder = InlineKeyboardBuilder()
  builder.button(text="🔐 Админ пароли", callback_data=SETTINGS_ADMIN_PASSWORD)
  builder.button(text="🔐 Етказиб берувчи пароли", callback_data=SETTINGS_SUPPLIER_PASSWORD)
  builder.button(text="🔔 Кам қолдиқ чегараси", callback_data=SETTINGS_THRESHOLD)
  builder.button(text="📁 Макс. файл ҳажми", callback_data=SETTINGS_UPLOAD_SIZE)
  builder.adjust(1)
  return builder.as_markup()
