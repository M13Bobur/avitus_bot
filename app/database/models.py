from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
  BigInteger,
  Boolean,
  DateTime,
  ForeignKey,
  Index,
  Integer,
  Numeric,
  String,
  Text,
  UniqueConstraint,
  func,
  text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
  pass


class UserRole(StrEnum):
  SUPER_ADMIN = "super_admin"
  SUPPLIER = "supplier"


class User(Base):
  __tablename__ = "users"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
  full_name: Mapped[str] = mapped_column(String(255), nullable=False)
  role: Mapped[str] = mapped_column(String(50), nullable=False)
  phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
  supplier_id: Mapped[int | None] = mapped_column(
    Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True
  )
  branch_id: Mapped[int | None] = mapped_column(
    Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True
  )
  created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), server_default=func.now(), nullable=False
  )

  supplier: Mapped["Supplier | None"] = relationship("Supplier", back_populates="users")
  branch: Mapped["Branch | None"] = relationship("Branch", back_populates="users")
  support_messages: Mapped[list["SupportMessage"]] = relationship(
    "SupportMessage", back_populates="user", passive_deletes=True
  )


class Supplier(Base):
  __tablename__ = "suppliers"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
  telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
  is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

  users: Mapped[list["User"]] = relationship("User", back_populates="supplier")
  inventory_records: Mapped[list["Inventory"]] = relationship(
    "Inventory", back_populates="supplier"
  )


class Branch(Base):
  __tablename__ = "branches"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

  users: Mapped[list["User"]] = relationship(
    "User", back_populates="branch", passive_deletes=True
  )
  inventory_records: Mapped[list["Inventory"]] = relationship(
    "Inventory", back_populates="branch", passive_deletes=True
  )


class Medicine(Base):
  __tablename__ = "medicines"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  name: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)

  inventory_records: Mapped[list["Inventory"]] = relationship(
    "Inventory", back_populates="medicine"
  )


class Inventory(Base):
  __tablename__ = "inventory"
  __table_args__ = (
    UniqueConstraint(
      "supplier_id", "branch_id", "medicine_id", "report_date",
      name="uq_inventory_supplier_branch_medicine_date",
    ),
    Index("ix_inventory_supplier_id", "supplier_id"),
    Index("ix_inventory_branch_id", "branch_id"),
    Index("ix_inventory_medicine_id", "medicine_id"),
    Index("ix_inventory_report_date", "report_date"),
  )

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  supplier_id: Mapped[int] = mapped_column(
    Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False
  )
  branch_id: Mapped[int] = mapped_column(
    Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False
  )
  medicine_id: Mapped[int] = mapped_column(
    Integer, ForeignKey("medicines.id", ondelete="CASCADE"), nullable=False
  )
  quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)
  report_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
  updated_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
  )

  supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="inventory_records")
  branch: Mapped["Branch"] = relationship("Branch", back_populates="inventory_records")
  medicine: Mapped["Medicine"] = relationship("Medicine", back_populates="inventory_records")


class ImportLog(Base):
  __tablename__ = "import_logs"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  user_id: Mapped[int] = mapped_column(
    Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
  )
  file_name: Mapped[str] = mapped_column(String(500), nullable=False)
  rows_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
  rows_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
  status: Mapped[str] = mapped_column(String(50), nullable=False)
  error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
  created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), server_default=func.now(), nullable=False
  )


class Notification(Base):
  __tablename__ = "notifications"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  supplier_id: Mapped[int] = mapped_column(
    Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True
  )
  medicine_id: Mapped[int] = mapped_column(
    Integer, ForeignKey("medicines.id", ondelete="CASCADE"), nullable=False
  )
  branch_id: Mapped[int] = mapped_column(
    Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False
  )
  quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
  threshold: Mapped[int] = mapped_column(Integer, nullable=False)
  is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
  created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), server_default=func.now(), nullable=False
  )


class AppSetting(Base):
  __tablename__ = "app_settings"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
  value: Mapped[str] = mapped_column(String(500), nullable=False)


class SupportMessage(Base):
  __tablename__ = "support_messages"
  __table_args__ = (
    Index("ix_support_messages_user_id_created_at", "user_id", "created_at"),
    Index(
      "ix_support_messages_user_id_unread",
      "user_id",
      postgresql_where=text("is_read = false"),
    ),
  )

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  user_id: Mapped[int] = mapped_column(
    Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
  )
  text: Mapped[str] = mapped_column(Text, nullable=False)
  is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
  created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), server_default=func.now(), nullable=False
  )

  user: Mapped["User"] = relationship("User", back_populates="support_messages")
