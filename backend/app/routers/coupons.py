from fastapi import APIRouter, Depends, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.auth import get_current_account, require_role
from app.database import get_db
from app.models import Account
from app.schemas import (
    CouponActionResponse,
    CouponHistoryEntry,
    CouponListItem,
    CouponLookupResponse,
    ImportResult,
    RedeemBypassRequest,
    RetireRequest,
)
from app.services import coupons as coupons_svc

router = APIRouter(tags=["coupons"])


def _ua(request: Request) -> str | None:
    return request.headers.get("user-agent")


# ---------------------------------------------------------------------------
# Manager endpointy — definovány PŘED {code} trasami, aby /import nebyl zachycen
# jako {code} parametr u budoucích POST /coupons/{code}/... tras.
# ---------------------------------------------------------------------------

@router.get("/coupons", response_model=list[CouponListItem])
def list_coupons(
    state: str | None = None,
    code: str | None = None,
    limit: int = Query(100, gt=0, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    account: Account = Depends(require_role("manager")),
):
    return coupons_svc.get_list(
        db, state_filter=state, code_filter=code, limit=limit, offset=offset
    )


@router.post("/coupons/import", response_model=ImportResult)
async def import_coupons(
    file: UploadFile,
    db: Session = Depends(get_db),
    account: Account = Depends(require_role("manager")),
):
    content = await file.read()
    return coupons_svc.import_csv(db, content, account)


# ---------------------------------------------------------------------------
# Operátorské endpointy
# ---------------------------------------------------------------------------

@router.get("/coupons/{code}", response_model=CouponLookupResponse)
def get_coupon(
    code: str,
    request: Request,
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
):
    return coupons_svc.lookup(db, code)


@router.post("/coupons/{code}/issue", response_model=CouponActionResponse)
def issue_coupon(
    code: str,
    request: Request,
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
):
    return coupons_svc.issue(db, code, account, _ua(request))


@router.post("/coupons/{code}/redeem", response_model=CouponActionResponse)
def redeem_coupon(
    code: str,
    request: Request,
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
):
    return coupons_svc.redeem(db, code, account, _ua(request))


@router.post("/coupons/{code}/redeem-bypass", response_model=CouponActionResponse)
def redeem_bypass(
    code: str,
    body: RedeemBypassRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
):
    return coupons_svc.redeem_bypass(db, code, account, _ua(request), body.reason)


# ---------------------------------------------------------------------------
# Manager endpointy pro konkrétní kupon
# ---------------------------------------------------------------------------

@router.get("/coupons/{code}/history", response_model=list[CouponHistoryEntry])
def coupon_history(
    code: str,
    db: Session = Depends(get_db),
    account: Account = Depends(require_role("manager")),
):
    return coupons_svc.get_history(db, code)


@router.post("/coupons/{code}/retire", response_model=CouponActionResponse)
def retire_coupon(
    code: str,
    body: RetireRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Account = Depends(require_role("manager")),
):
    return coupons_svc.retire(db, code, account, _ua(request), body.reason)
