from aiogram.fsm.state import State, StatesGroup


class AdminSettingsStates(StatesGroup):
  waiting_admin_password = State()
  waiting_supplier_password = State()
  waiting_threshold = State()
  waiting_upload_size = State()
