from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
  def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
    self._session = session
    self._model = model

  async def get_by_id(self, entity_id: int) -> ModelT | None:
    result = await self._session.execute(
      select(self._model).where(self._model.id == entity_id)
    )
    return result.scalar_one_or_none()

  async def get_all(self) -> list[ModelT]:
    result = await self._session.execute(select(self._model))
    return list(result.scalars().all())

  async def create(self, **kwargs: Any) -> ModelT:
    entity = self._model(**kwargs)
    self._session.add(entity)
    await self._session.flush()
    return entity

  async def count(self) -> int:
    result = await self._session.execute(
      select(func.count()).select_from(self._model)
    )
    return result.scalar_one()
