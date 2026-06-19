from aiogram.fsm.state import State, StatesGroup


class AdminUploadStates(StatesGroup):
  waiting_branch = State()
  waiting_file = State()
