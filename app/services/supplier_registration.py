class SupplierRegistrationError(Exception):
  pass


class SupplierRegistrationService:
  def __init__(self, session) -> None:
    from app.repositories.supplier import SupplierRepository
    from app.repositories.user import UserRepository

    self._session = session
    self._user_repo = UserRepository(session)
    self._supplier_repo = SupplierRepository(session)

  async def get_available_suppliers(self) -> list:
    suppliers = await self._supplier_repo.get_active_suppliers()
    return sorted(suppliers, key=lambda s: s.name.lower())

  async def register_admin_user(
    self, telegram_id: int, full_name: str, phone: str | None = None
  ) -> None:
    from app.database.models import UserRole

    existing_user = await self._user_repo.get_by_telegram_id(telegram_id)
    if existing_user is not None:
      raise SupplierRegistrationError("Сиз аллақачон рўйхатдан ўтгансиз.")

    await self._user_repo.create(
      telegram_id=telegram_id,
      full_name=full_name,
      role=UserRole.SUPER_ADMIN.value,
      phone=phone,
      supplier_id=None,
    )

  async def register_supplier_user(
    self,
    telegram_id: int,
    full_name: str,
    phone: str,
    supplier_id: int,
  ) -> None:
    from app.database.models import UserRole

    existing_user = await self._user_repo.get_by_telegram_id(telegram_id)
    if existing_user is not None:
      raise SupplierRegistrationError("Сиз аллақачон рўйхатдан ўтгансиз.")

    supplier = await self._supplier_repo.get_by_id(supplier_id)
    if supplier is None:
      raise SupplierRegistrationError("Фирма топилмади.")

    if not supplier.is_active:
      raise SupplierRegistrationError("Бу фирма фаол эмас.")

    if supplier.telegram_id is not None:
      raise SupplierRegistrationError("Бу фирма бошқа фойдаланувчига боғланган.")

    await self._user_repo.create(
      telegram_id=telegram_id,
      full_name=full_name,
      role=UserRole.SUPPLIER.value,
      phone=phone,
      supplier_id=supplier_id,
    )

    supplier.telegram_id = telegram_id
    await self._session.flush()
