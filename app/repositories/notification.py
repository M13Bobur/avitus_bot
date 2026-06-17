from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
  def __init__(self, session: AsyncSession) -> None:
    super().__init__(session, Notification)

  async def create_notification(
    self,
    supplier_id: int,
    medicine_id: int,
    branch_id: int,
    quantity: Decimal,
    threshold: int,
  ) -> Notification:
    return await self.create(
      supplier_id=supplier_id,
      medicine_id=medicine_id,
      branch_id=branch_id,
      quantity=quantity,
      threshold=threshold,
      is_read=False,
    )
