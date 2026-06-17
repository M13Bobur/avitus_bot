#!/usr/bin/env python3
"""Seed initial admin user into the database."""

import asyncio
import sys

from sqlalchemy import select

from app.database.engine import async_session_factory
from app.database.models import User, UserRole


async def seed_admin(telegram_id: int, full_name: str) -> None:
  async with async_session_factory() as session:
    result = await session.execute(
      select(User).where(User.telegram_id == telegram_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
      print(f"User with telegram_id={telegram_id} already exists.")
      return

    user = User(
      telegram_id=telegram_id,
      full_name=full_name,
      role=UserRole.SUPER_ADMIN.value,
    )
    session.add(user)
    await session.commit()
    print(f"Admin user '{full_name}' (telegram_id={telegram_id}) created successfully.")


if __name__ == "__main__":
  if len(sys.argv) < 3:
    print("Usage: python scripts/seed_admin.py <telegram_id> <full_name>")
    sys.exit(1)

  tg_id = int(sys.argv[1])
  name = sys.argv[2]
  asyncio.run(seed_admin(tg_id, name))
