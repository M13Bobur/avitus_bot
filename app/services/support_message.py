import html
from datetime import datetime

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.texts import MSG_EMPTY, MSG_TOO_LONG
from app.database.models import User, UserRole
from app.logging_config import get_logger
from app.repositories.support_message import MessageConversation, SupportMessageRepository
from app.repositories.user import UserRepository
from app.utils.telegram import split_message_parts

logger = get_logger(__name__)

MAX_MESSAGE_LENGTH = 4000


class SupportMessageError(Exception):
  pass


class SupportMessageService:
  def __init__(self, session: AsyncSession) -> None:
    self._session = session
    self._message_repo = SupportMessageRepository(session)
    self._user_repo = UserRepository(session)

  async def send_message(self, user: User, text: str):
    cleaned = text.strip()
    if not cleaned:
      raise SupportMessageError(MSG_EMPTY)
    if len(cleaned) > MAX_MESSAGE_LENGTH:
      raise SupportMessageError(MSG_TOO_LONG)

    return await self._message_repo.create_message(user.id, cleaned)

  async def get_conversations(self) -> list[MessageConversation]:
    return await self._message_repo.get_conversations()

  async def get_user_messages(self, user_id: int) -> tuple[User | None, list]:
    user = await self._user_repo.get_with_supplier(user_id)
    if user is None:
      return None, []

    messages = await self._message_repo.get_by_user_id(user_id)
    await self._message_repo.mark_as_read(user_id)
    return user, messages

  async def count_total_unread(self) -> int:
    return await self._message_repo.count_total_unread()

  async def notify_admins(self, bot: Bot, sender: User, message_text: str) -> int:
    sender_with_relations = await self._user_repo.get_with_supplier(sender.id)
    if sender_with_relations is not None:
      sender = sender_with_relations

    admins = await self._user_repo.get_all_by_role(UserRole.SUPER_ADMIN)
    if not admins:
      return 0

    sender_name = html.escape(sender.full_name)
    firm = html.escape(sender.supplier.name) if sender.supplier is not None else "—"
    branch = html.escape(sender.branch.name) if sender.branch is not None else "—"
    preview = html.escape(message_text)
    if len(preview) > 300:
      preview = preview[:300] + "…"

    notification_lines = [
      "📩 <b>Янги хабар</b>",
      "",
      f"👤 {sender_name}",
      f"🏭 {firm}",
      f"📍 {branch}",
      "",
      preview,
    ]

    sent = 0
    for admin in admins:
      try:
        await bot.send_message(
          admin.telegram_id,
          "\n".join(notification_lines),
          parse_mode="HTML",
        )
        sent += 1
      except Exception as exc:
        logger.warning(
          "admin_message_notify_failed",
          admin_id=admin.id,
          telegram_id=admin.telegram_id,
          error=str(exc),
        )
    return sent


def format_user_messages(user: User, messages: list) -> list[str]:
  sender_name = html.escape(user.full_name)
  firm = html.escape(user.supplier.name) if user.supplier is not None else "—"
  branch = html.escape(user.branch.name) if user.branch is not None else "—"
  phone = html.escape(user.phone or "—")

  header = [
    f"💬 <b>{sender_name}</b> хабарлар",
    f"🏭 {firm} · 📍 {branch}",
    f"📱 {phone}",
    f"📨 Жами: {len(messages)} та",
    "",
    "───────────────",
  ]

  if not messages:
    header.append("")
    header.append("<i>Хабарлар йо‘қ.</i>")
    return ["\n".join(header)]

  lines = list(header)
  for message in messages:
    timestamp = _format_timestamp(message.created_at)
    text = html.escape(message.text)
    lines.extend(["", f"🕐 {timestamp}", text])

  return split_message_parts(lines)


def format_conversations_list(conversations: list[MessageConversation]) -> str:
  if not conversations:
    return "💬 <b>Хабарлар</b>\n\nХозирча хеч ким хабар юбормаган."

  total_unread = sum(item.unread_count for item in conversations)
  lines = [
    "💬 <b>Хабарлар</b>",
    f"👥 Сухбатлар: {len(conversations)} та",
  ]
  if total_unread:
    lines.append(f"🔔 Ўқилмаган: {total_unread} та")
  lines.extend(["", "Фойдаланувчини танланг:"])
  return "\n".join(lines)


def _format_timestamp(value: datetime) -> str:
  return value.strftime("%Y-%m-%d %H:%M")
