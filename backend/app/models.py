import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AccountRole(str, enum.Enum):
    operator = "operator"
    manager = "manager"
    master = "master"


class CouponState(str, enum.Enum):
    VOLNA = "VOLNA"
    K_UPLATNENI = "K_UPLATNENI"
    VYRAZENA = "VYRAZENA"


class LogAction(str, enum.Enum):
    VYDANI = "VYDANI"
    UPLATNENI = "UPLATNENI"
    VYRAZENI = "VYRAZENI"
    IMPORT = "IMPORT"


class LogResult(str, enum.Enum):
    OK = "OK"
    ODMITNUTO = "ODMITNUTO"
    BYPASS = "BYPASS"


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    accounts: Mapped[list["Account"]] = relationship(back_populates="restaurant")
    coupon_logs: Mapped[list["CouponLog"]] = relationship(back_populates="restaurant")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[AccountRole] = mapped_column(
        SAEnum(AccountRole, name="account_role"), nullable=False
    )
    restaurant_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=True
    )
    baseline_user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    restaurant: Mapped[Optional["Restaurant"]] = relationship(back_populates="accounts")
    coupon_logs: Mapped[list["CouponLog"]] = relationship(back_populates="account")


class Coupon(Base):
    __tablename__ = "coupons"

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    state: Mapped[CouponState] = mapped_column(
        SAEnum(CouponState, name="coupon_state"),
        nullable=False,
        default=CouponState.VOLNA,
        server_default="VOLNA",
    )
    retired_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    logs: Mapped[list["CouponLog"]] = relationship(
        primaryjoin="Coupon.code == foreign(CouponLog.coupon_code)",
        back_populates="coupon",
    )


class CouponLog(Base):
    __tablename__ = "coupon_logs"
    __table_args__ = (
        Index("ix_coupon_logs_coupon_code", "coupon_code"),
        Index("ix_coupon_logs_is_suspicious", "is_suspicious"),
        Index("ix_coupon_logs_server_time", "server_time"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # coupon_code je TEXT (ne FK constraint) — log zůstává i po případném vyřazení kuponu
    coupon_code: Mapped[str] = mapped_column(Text, nullable=False)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False)
    restaurant_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=True
    )
    action: Mapped[LogAction] = mapped_column(
        SAEnum(LogAction, name="log_action"), nullable=False
    )
    result: Mapped[LogResult] = mapped_column(
        SAEnum(LogResult, name="log_result"), nullable=False
    )
    is_suspicious: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    suspicious_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    server_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # coupon_code není FK v DB, ale relationship přes primární klíč pro pohodlné dotazy
    coupon: Mapped[Optional["Coupon"]] = relationship(
        primaryjoin="foreign(CouponLog.coupon_code) == Coupon.code",
        back_populates="logs",
    )
    account: Mapped["Account"] = relationship(back_populates="coupon_logs")
    restaurant: Mapped[Optional["Restaurant"]] = relationship(back_populates="coupon_logs")
