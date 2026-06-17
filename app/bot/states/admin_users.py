from aiogram.fsm.state import State, StatesGroup


class AdminUsersStates(StatesGroup):
  waiting_search = State()
