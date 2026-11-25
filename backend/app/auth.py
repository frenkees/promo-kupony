from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.responses import Response
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Account, AccountRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ROLE_HIERARCHY = {
    AccountRole.operator: 0,
    AccountRole.manager: 1,
    AccountRole.master: 2,
}


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(account_id: int, role: str, restaurant_id: Optional[int]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_EXPIRE_DAYS)
    payload = {
        "sub": str(account_id),
        "role": role,
        "restaurant_id": restaurant_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=settings.JWT_EXPIRE_DAYS * 86400,
    )


def get_current_account(
    request: Request,
    db: Session = Depends(get_db),
) -> Account:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Nepřihlášen")
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Platnost přihlášení vypršela")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Neplatný token (podpis): {str(e)}")

    try:
        account_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail=f"Neplatný token (data): {str(e)} | Hodnota: {payload.get('sub')}")

    account = db.get(Account, account_id)
    if not account or not account.active:
        raise HTTPException(status_code=401, detail="Účet neexistuje nebo je deaktivován")
    return account


def require_role(minimum_role: str):
    """Dependency factory — vrátí závislost pro minimální požadovanou roli.

    Hierarchie: master ≥ manager ≥ operator.
    """
    min_level = ROLE_HIERARCHY[AccountRole(minimum_role)]

    def dependency(account: Account = Depends(get_current_account)) -> Account:
        if ROLE_HIERARCHY[account.role] < min_level:
            raise HTTPException(status_code=403, detail="Nedostatečná oprávnění")
        return account

    return dependency
