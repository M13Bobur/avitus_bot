from aiogram.fsm.state import State, StatesGroup


class SupplierStates(StatesGroup):
  waiting_search_query = State()
