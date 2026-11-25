from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import hash_password, require_role
from app.database import get_db
from app.models import Account, AccountRole, Restaurant
from app.schemas import (
    AccountCreate,
    AccountListItem,
    ResetPasswordRequest,
    ToggleActiveResponse,
)

router = APIRouter(tags=["accounts"])


def _account_to_dict(account: Account, restaurant_name: str | None) -> dict:
    return {
        "id": account.id,
        "login": account.login,
        "role": account.role.value,
        "restaurant_id": account.restaurant_id,
        "restaurant_name": restaurant_name,
        "active": account.active,
        "must_change_password": account.must_change_password,
        "created_at": account.created_at,
    }


@router.get("/accounts", response_model=list[AccountListItem])
def list_accounts(
    db: Session = Depends(get_db),
    _account=Depends(require_role("master")),
):
    rows = db.execute(
        select(Account, Restaurant.name.label("restaurant_name"))
        .outerjoin(Restaurant, Account.restaurant_id == Restaurant.id)
        .order_by(Account.login)
    ).all()
    return [_account_to_dict(r.Account, r.restaurant_name) for r in rows]


@router.post("/accounts", response_model=AccountListItem, status_code=201)
def create_account(
    body: AccountCreate,
    db: Session = Depends(get_db),
    _master=Depends(require_role("master")),
):
    # Validace role
    try:
        role = AccountRole(body.role)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Neznámá role: {body.role!r}")

    # Operátor musí mít pobočku
    if role == AccountRole.operator and body.restaurant_id is None:
        raise HTTPException(
            status_code=422,
            detail="Operátorský účet musí mít přiřazenou pobočku (restaurant_id)",
        )

    # Manager/master nemá pobočku
    restaurant_id = body.restaurant_id if role == AccountRole.operator else None

    # Ověření existence pobočky pro operátora
    if restaurant_id is not None and db.get(Restaurant, restaurant_id) is None:
        raise HTTPException(status_code=404, detail="Pobočka nenalezena")

    # Unikátní login
    if db.scalar(select(Account).where(Account.login == body.login)) is not None:
        raise HTTPException(status_code=409, detail=f"Login {body.login!r} je již obsazen")

    account = Account(
        login=body.login,
        password_hash=hash_password(body.password),
        role=role,
        restaurant_id=restaurant_id,
        must_change_password=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    restaurant_name = (
        db.scalar(select(Restaurant.name).where(Restaurant.id == restaurant_id))
        if restaurant_id is not None
        else None
    )
    return _account_to_dict(account, restaurant_name)


@router.post("/accounts/{account_id}/reset-password")
def reset_password(
    account_id: int,
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
    _master=Depends(require_role("master")),
):
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Účet nenalezen")
    account.password_hash = hash_password(body.new_password)
    account.must_change_password = True
    db.commit()
    return {"ok": True}


@router.post("/accounts/{account_id}/toggle-active", response_model=ToggleActiveResponse)
def toggle_active(
    account_id: int,
    db: Session = Depends(get_db),
    _master=Depends(require_role("master")),
):
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Účet nenalezen")
    account.active = not account.active
    db.commit()
    return ToggleActiveResponse(id=account.id, active=account.active)
