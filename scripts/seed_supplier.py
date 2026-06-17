#!/usr/bin/env python3
"""Seed a supplier user linked to a supplier."""

import asyncio
import sys

from sqlalchemy import select

from app.database.engine import async_session_factory
from app.database.models import Supplier, User, UserRole


async def seed_supplier(
  telegram_id: int,
  full_name: str,
  supplier_name: str,
) -> None:
  async with async_session_factory() as session:
    result = await session.execute(
      select(User).where(User.telegram_id == telegram_id)
    )
    if result.scalar_one_or_none():
      print(f"User with telegram_id={telegram_id} already exists.")
      return

    result = await session.execute(
      select(Supplier).where(Supplier.name == supplier_name)
    )
    supplier = result.scalar_one_or_none()

    if supplier is None:
      supplier = Supplier(name=supplier_name, is_active=True)
      session.add(supplier)
      await session.flush()

    user = User(
      telegram_id=telegram_id,
      full_name=full_name,
      role=UserRole.SUPPLIER.value,
      supplier_id=supplier.id,
    )
    session.add(user)
    await session.commit()
    print(
      f"Supplier user '{full_name}' linked to '{supplier_name}' "
      f"(telegram_id={telegram_id}) created successfully."
    )


if __name__ == "__main__":
  if len(sys.argv) < 4:
    print("Usage: python scripts/seed_supplier.py <telegram_id> <full_name> <supplier_name>")
    sys.exit(1)

  tg_id = int(sys.argv[1])
  name = sys.argv[2]
  supplier = sys.argv[3]
  asyncio.run(seed_supplier(tg_id, name, supplier))
