from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    login: str
    password: str


class LoginResponse(BaseModel):
    role: str
    restaurant_id: Optional[int] = None
    must_change_password: bool


class MeResponse(BaseModel):
    account_id: int
    login: str
    role: str
    restaurant_id: Optional[int] = None
    restaurant_name: Optional[str] = None
    must_change_password: bool


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


# --- Kuponová schémata ---

class CouponLookupResponse(BaseModel):
    code: str
    state: str
    last_issue: Optional[datetime] = None


class CouponActionResponse(BaseModel):
    code: str
    state: str


class RedeemBypassRequest(BaseModel):
    reason: str = Field(min_length=1)


class RetireRequest(BaseModel):
    reason: str = Field(min_length=1)


# --- Manažerská schémata ---

class CouponListItem(BaseModel):
    code: str
    state: str
    created_at: datetime
    updated_at: datetime


class CouponHistoryEntry(BaseModel):
    id: int
    action: str
    result: str
    account_login: str
    restaurant_name: Optional[str]
    server_time: datetime
    is_suspicious: bool
    suspicious_reason: Optional[str]
    user_agent: Optional[str]


class RestaurantStats(BaseModel):
    restaurant_id: int
    name: str
    issued: int
    redeemed: int


class DashboardOverview(BaseModel):
    open_liability: int
    redemption_rate: float
    fund: dict[str, int]
    by_restaurant: list[RestaurantStats]


class SuspiciousEntry(BaseModel):
    id: int
    coupon_code: str
    action: str
    result: str
    account_login: str
    restaurant_name: Optional[str]
    server_time: datetime
    suspicious_reason: Optional[str]
    user_agent: Optional[str]


class ImportResult(BaseModel):
    added: int
    skipped: int


# --- Master schémata ---

class RestaurantCreate(BaseModel):
    name: str = Field(min_length=1)


class RestaurantUpdate(BaseModel):
    name: str = Field(min_length=1)


class RestaurantResponse(BaseModel):
    id: int
    name: str
    created_at: datetime


class AccountCreate(BaseModel):
    login: str = Field(min_length=1)
    password: str = Field(min_length=8)
    role: str
    restaurant_id: Optional[int] = None


class AccountListItem(BaseModel):
    id: int
    login: str
    role: str
    restaurant_id: Optional[int]
    restaurant_name: Optional[str]
    active: bool
    must_change_password: bool
    created_at: datetime


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8)


class ToggleActiveResponse(BaseModel):
    id: int
    active: bool
