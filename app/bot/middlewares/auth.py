from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.services.auth import AuthService


class AuthMiddleware(BaseMiddleware):
  async def __call__(
    self,
    handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
    event: TelegramObject,
    data: dict[str, Any],
  ) -> Any:
    user = data.get("event_from_user")
    data["db_user"] = None

    if user is not None:
      session = data["session"]
      auth_service = AuthService(session)
      data["db_user"] = await auth_service.get_user(user.id)

    return await handler(event, data)
