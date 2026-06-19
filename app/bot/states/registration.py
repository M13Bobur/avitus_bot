from aiogram.fsm.state import State, StatesGroup


class SupplierRegistrationStates(StatesGroup):
  waiting_password = State()
  waiting_branch = State()
  waiting_company = State()
  waiting_phone = State()
  waiting_admin_phone = State()
