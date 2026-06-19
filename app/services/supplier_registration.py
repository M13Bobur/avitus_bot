class SupplierRegistrationError(Exception):
  pass


class SupplierRegistrationService:
  def __init__(self, session) -> None:
    from app.repositories.branch import BranchRepository
    from app.repositories.supplier import SupplierRepository
    from app.repositories.user import UserRepository

    self._session = session
    self._user_repo = UserRepository(session)
    self._supplier_repo = SupplierRepository(session)
    self._branch_repo = BranchRepository(session)

  async def get_branches(self) -> list:
    return await self._branch_repo.get_all_ordered()

  async def get_available_suppliers(self, branch_id: int) -> list:
    suppliers = await self._supplier_repo.get_active_suppliers_for_branch(branch_id)
    return sorted(suppliers, key=lambda s: s.name.lower())

  async def get_busy_supplier_ids(self, branch_id: int) -> set[int]:
    return await self._user_repo.get_registered_supplier_ids_for_branch(branch_id)

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
    branch_id: int,
  ) -> None:
    from sqlalchemy.exc import IntegrityError

    from app.database.models import UserRole

    existing_user = await self._user_repo.get_by_telegram_id(telegram_id)
    if existing_user is not None:
      raise SupplierRegistrationError("Сиз аллақачон рўйхатдан ўтгансиз.")

    branch = await self._branch_repo.get_by_id(branch_id)
    if branch is None:
      raise SupplierRegistrationError("Филиал топилмади.")

    supplier = await self._supplier_repo.get_by_id(supplier_id)
    if supplier is None:
      raise SupplierRegistrationError("Фирма топилмади.")

    if not supplier.is_active:
      raise SupplierRegistrationError("Бу фирма фаол эмас.")

    registered = await self._user_repo.get_supplier_user_for_branch(
      supplier_id, branch_id
    )
    if registered is not None:
      raise SupplierRegistrationError("Бу фирма бу филиалда аллақачон рўйхатдан ўтган.")

    available = await self.get_available_suppliers(branch_id)
    if supplier_id not in {item.id for item in available}:
      raise SupplierRegistrationError("Бу фирма танланган филиалда топилмади.")

    await self._user_repo.create(
      telegram_id=telegram_id,
      full_name=full_name,
      role=UserRole.SUPPLIER.value,
      phone=phone,
      supplier_id=supplier_id,
      branch_id=branch_id,
    )
    try:
      await self._session.flush()
    except IntegrityError as exc:
      raise SupplierRegistrationError(
        "Бу фирма бу филиалда аллақачон рўйхатдан ўтган."
      ) from exc
