from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AppSetting
from app.repositories.base import BaseRepository


class AppSettingRepository(BaseRepository[AppSetting]):
  def __init__(self, session: AsyncSession) -> None:
    super().__init__(session, AppSetting)

  async def get_by_key(self, key: str) -> AppSetting | None:
    result = await self._session.execute(
      select(AppSetting).where(AppSetting.key == key)
    )
    return result.scalar_one_or_none()

  async def get_value(self, key: str, default: str = "") -> str:
    setting = await self.get_by_key(key)
    return setting.value if setting else default

  async def set_value(self, key: str, value: str) -> AppSetting:
    setting = await self.get_by_key(key)
    if setting is not None:
      setting.value = value
      await self._session.flush()
      return setting
    return await self.create(key=key, value=value)
