from aiogram import Router

from app.bot.handlers.admin import router as admin_router
from app.bot.handlers.admin_commands import router as admin_commands_router
from app.bot.handlers.admin_settings import router as admin_settings_router
from app.bot.handlers.admin_users import router as admin_users_router
from app.bot.handlers.supplier import router as supplier_router
from app.bot.handlers.supplier_registration import router as supplier_registration_router


def setup_routers() -> Router:
  root_router = Router()
  root_router.include_router(supplier_registration_router)
  root_router.include_router(admin_settings_router)
  root_router.include_router(admin_users_router)
  root_router.include_router(admin_router)
  root_router.include_router(admin_commands_router)
  root_router.include_router(supplier_router)
  return root_router
