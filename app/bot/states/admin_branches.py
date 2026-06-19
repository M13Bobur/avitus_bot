from aiogram.fsm.state import State, StatesGroup


class AdminBranchesStates(StatesGroup):
  waiting_branch_name = State()
