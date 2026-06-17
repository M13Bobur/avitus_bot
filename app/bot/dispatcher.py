from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import setup_routers
from app.bot.middlewares.auth import AuthMiddleware
from app.bot.middlewares.database import DatabaseMiddleware
from app.config import settings


def create_bot() -> Bot:
  return Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
  )


def create_dispatcher() -> Dispatcher:
  dp = Dispatcher(storage=MemoryStorage())
  dp.update.middleware(DatabaseMiddleware())
  dp.update.middleware(AuthMiddleware())
  dp.include_router(setup_routers())
  return dp
