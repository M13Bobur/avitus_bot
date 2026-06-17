from typing import Any

from aiogram.filters import BaseFilter

from app.database.models import User, UserRole


class IsSuperAdmin(BaseFilter):
  async def __call__(self, event: Any, **kwargs: Any) -> bool:
    db_user: User | None = kwargs.get("db_user")
    return db_user is not None and db_user.role == UserRole.SUPER_ADMIN.value


class IsSupplier(BaseFilter):
  async def __call__(self, event: Any, **kwargs: Any) -> bool:
    db_user: User | None = kwargs.get("db_user")
    return db_user is not None and db_user.role == UserRole.SUPPLIER.value
