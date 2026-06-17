import asyncio

from app.bot.dispatcher import create_bot, create_dispatcher
from app.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


async def main() -> None:
  setup_logging()
  logger.info("bot_starting")

  bot = create_bot()
  dp = create_dispatcher()

  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
