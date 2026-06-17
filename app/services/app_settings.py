from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories.app_setting import AppSettingRepository

LOW_STOCK_KEY = "low_stock_threshold"
SUPPLIER_PASSWORD_KEY = "supplier_registration_password"
ADMIN_PASSWORD_KEY = "admin_registration_password"
MAX_UPLOAD_KEY = "max_upload_size_mb"


class AppSettingsService:
  def __init__(self, session: AsyncSession) -> None:
    self._repo = AppSettingRepository(session)

  async def get_low_stock_threshold(self) -> int:
    value = await self._repo.get_value(LOW_STOCK_KEY, str(settings.low_stock_threshold))
    try:
      return int(value)
    except ValueError:
      return settings.low_stock_threshold

  async def set_low_stock_threshold(self, threshold: int) -> None:
    await self._repo.set_value(LOW_STOCK_KEY, str(threshold))

  async def get_supplier_password(self) -> str:
    return await self._repo.get_value(
      SUPPLIER_PASSWORD_KEY,
      settings.supplier_registration_password,
    )

  async def set_supplier_password(self, password: str) -> None:
    if len(password) < 4:
      raise ValueError("Парол камида 4 белгидан иборат бўлиши керак.")
    await self._repo.set_value(SUPPLIER_PASSWORD_KEY, password)

  async def get_admin_password(self) -> str:
    return await self._repo.get_value(
      ADMIN_PASSWORD_KEY,
      settings.admin_registration_password,
    )

  async def set_admin_password(self, password: str) -> None:
    if len(password) < 4:
      raise ValueError("Парол камида 4 белгидан иборат бўлиши керак.")
    await self._repo.set_value(ADMIN_PASSWORD_KEY, password)

  async def get_max_upload_size_mb(self) -> int:
    value = await self._repo.get_value(MAX_UPLOAD_KEY, str(settings.max_upload_size_mb))
    try:
      return int(value)
    except ValueError:
      return settings.max_upload_size_mb

  async def set_max_upload_size_mb(self, size_mb: int) -> None:
    if size_mb < 1 or size_mb > 100:
      raise ValueError("Ҳажм 1 дан 100 MB гача бўлиши керак.")
    await self._repo.set_value(MAX_UPLOAD_KEY, str(size_mb))

  async def get_summary(self) -> dict[str, str | int]:
    return {
      "admin_password": await self.get_admin_password(),
      "supplier_password": await self.get_supplier_password(),
      "threshold": await self.get_low_stock_threshold(),
      "max_upload_mb": await self.get_max_upload_size_mb(),
    }
