from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.auth import (
    create_token,
    get_current_account,
    hash_password,
    set_auth_cookie,
    verify_password,
)
from app.database import get_db
from app.limiter import limiter
from app.models import Account, AccountRole, Restaurant
from app.schemas import ChangePasswordRequest, LoginRequest, LoginResponse, MeResponse

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    account: Account | None = db.query(Account).filter(Account.login == body.login).first()
    if not account or not verify_password(body.password, account.password_hash):
        raise HTTPException(status_code=401, detail="Nesprávné přihlašovací údaje")
    if not account.active:
        raise HTTPException(status_code=401, detail="Účet je deaktivován")

    # Uložení baseline User-Agent operátora při prvním přihlášení
    ua = request.headers.get("user-agent")
    if account.role == AccountRole.operator and account.baseline_user_agent is None and ua:
        account.baseline_user_agent = ua
        db.commit()

    token = create_token(account.id, account.role.value, account.restaurant_id)
    set_auth_cookie(response, token)

    return LoginResponse(
        role=account.role.value,
        restaurant_id=account.restaurant_id,
        must_change_password=account.must_change_password,
    )


@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"ok": True}


@router.get("/auth/me", response_model=MeResponse)
async def me(account: Account = Depends(get_current_account), db: Session = Depends(get_db)):
    restaurant_name = None
    if account.restaurant_id:
        r = db.get(Restaurant, account.restaurant_id)
        restaurant_name = r.name if r else None
    return MeResponse(
        account_id=account.id,
        login=account.login,
        role=account.role.value,
        restaurant_id=account.restaurant_id,
        restaurant_name=restaurant_name,
        must_change_password=account.must_change_password,
    )


@router.post("/auth/change-password")
async def change_password(
    body: ChangePasswordRequest,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    if not verify_password(body.old_password, account.password_hash):
        raise HTTPException(status_code=400, detail="Nesprávné současné heslo")
    account.password_hash = hash_password(body.new_password)
    account.must_change_password = False
    db.commit()
    return {"ok": True}
