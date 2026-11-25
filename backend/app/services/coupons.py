import csv
import io
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import desc, select, text
from sqlalchemy.orm import Session

from app.models import Account, Coupon, CouponLog, CouponState, LogAction, LogResult, Restaurant
from app.services.audit import write_log


def _atomic_update(
    db: Session,
    code: str,
    expected_state: CouponState,
    new_state: CouponState,
) -> int:
    """Podmíněný UPDATE stavu kuponu. Vrátí počet změněných řádků (0 nebo 1)."""
    result = db.execute(
        text(
            "UPDATE coupons SET state = :new, updated_at = now() "
            "WHERE code = :code AND state = :expected"
        ),
        {"new": new_state.value, "code": code, "expected": expected_state.value},
    )
    return result.rowcount


def lookup(db: Session, code: str) -> dict:
    """Přečte stav kuponu a timestamp posledního vydání. Nepíše log."""
    coupon = db.get(Coupon, code)
    if coupon is None:
        raise HTTPException(status_code=404, detail="Kupon nenalezen")

    last_issue = db.scalar(
        select(CouponLog.server_time)
        .where(
            CouponLog.coupon_code == code,
            CouponLog.action == LogAction.VYDANI,
        )
        .order_by(desc(CouponLog.server_time))
        .limit(1)
    )

    return {"code": coupon.code, "state": coupon.state.value, "last_issue": last_issue}


def issue(
    db: Session,
    code: str,
    account: Account,
    user_agent: Optional[str],
) -> dict:
    """Atomický přechod VOLNA → K_UPLATNENI + zápis logu."""
    coupon = db.get(Coupon, code)
    if coupon is None:
        raise HTTPException(status_code=404, detail="Kupon nenalezen")

    current_state = coupon.state  # uložíme před UPDATE pro případ 409

    if _atomic_update(db, code, CouponState.VOLNA, CouponState.K_UPLATNENI) == 0:
        raise HTTPException(
            status_code=409,
            detail={"message": "Kupon není ve stavu VOLNA", "current_state": current_state.value},
        )

    write_log(
        db,
        coupon_code=code,
        account=account,
        action=LogAction.VYDANI,
        result=LogResult.OK,
        user_agent=user_agent,
    )
    db.commit()
    return {"code": code, "state": CouponState.K_UPLATNENI.value}


def redeem(
    db: Session,
    code: str,
    account: Account,
    user_agent: Optional[str],
) -> dict:
    """Atomický přechod K_UPLATNENI → VOLNA + zápis logu."""
    coupon = db.get(Coupon, code)
    if coupon is None:
        raise HTTPException(status_code=404, detail="Kupon nenalezen")

    current_state = coupon.state

    if _atomic_update(db, code, CouponState.K_UPLATNENI, CouponState.VOLNA) == 0:
        raise HTTPException(
            status_code=409,
            detail={"message": "Kupon není ve stavu K_UPLATNENI", "current_state": current_state.value},
        )

    write_log(
        db,
        coupon_code=code,
        account=account,
        action=LogAction.UPLATNENI,
        result=LogResult.OK,
        user_agent=user_agent,
    )
    db.commit()
    return {"code": code, "state": CouponState.VOLNA.value}


def redeem_bypass(
    db: Session,
    code: str,
    account: Account,
    user_agent: Optional[str],
    reason: str,
) -> dict:
    """Bypass uplatnění (VOLNA→VOLNA) + log BYPASS + is_suspicious=True."""
    coupon = db.get(Coupon, code)
    if coupon is None:
        raise HTTPException(status_code=404, detail="Kupon nenalezen")

    if coupon.state == CouponState.VYRAZENA:
        raise HTTPException(
            status_code=409,
            detail={"message": "Vyřazená karta se neuplatní ani přesto", "current_state": "VYRAZENA"},
        )
    if coupon.state != CouponState.VOLNA:
        raise HTTPException(
            status_code=409,
            detail={"message": "Bypass je možný pouze pro stav VOLNA", "current_state": coupon.state.value},
        )

    # Atomicky ověří, že stav je stále VOLNA (ochrana před race condition)
    if _atomic_update(db, code, CouponState.VOLNA, CouponState.VOLNA) == 0:
        raise HTTPException(
            status_code=409,
            detail={"message": "Stav kuponu se mezitím změnil", "current_state": coupon.state.value},
        )

    write_log(
        db,
        coupon_code=code,
        account=account,
        action=LogAction.UPLATNENI,
        result=LogResult.BYPASS,
        user_agent=user_agent,
        bypass_reason=reason,
    )
    db.commit()
    return {"code": code, "state": CouponState.VOLNA.value}


# ---------------------------------------------------------------------------
# Manažerské funkce
# ---------------------------------------------------------------------------

def get_list(
    db: Session,
    state_filter: Optional[str] = None,
    code_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Seznam kupónů s volitelným filtrem stavu a kódu + stránkováním."""
    stmt = select(Coupon).order_by(Coupon.code)
    if state_filter:
        try:
            stmt = stmt.where(Coupon.state == CouponState(state_filter))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Neznámý stav: {state_filter}")
    if code_filter:
        stmt = stmt.where(Coupon.code.ilike(f"%{code_filter}%"))

    stmt = stmt.limit(limit).offset(offset)
    coupons = db.scalars(stmt).all()
    return [
        {
            "code": c.code,
            "state": c.state.value,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        }
        for c in coupons
    ]


def get_history(db: Session, code: str) -> list[dict]:
    """Chronologická osa coupon_logs pro daný kód."""
    if db.get(Coupon, code) is None:
        raise HTTPException(status_code=404, detail="Kupon nenalezen")

    stmt = (
        select(CouponLog, Account.login.label("account_login"), Restaurant.name.label("restaurant_name"))
        .join(Account, CouponLog.account_id == Account.id)
        .outerjoin(Restaurant, CouponLog.restaurant_id == Restaurant.id)
        .where(CouponLog.coupon_code == code)
        .order_by(CouponLog.server_time)
    )
    rows = db.execute(stmt).all()
    return [
        {
            "id": r.CouponLog.id,
            "action": r.CouponLog.action.value,
            "result": r.CouponLog.result.value,
            "account_login": r.account_login,
            "restaurant_name": r.restaurant_name,
            "server_time": r.CouponLog.server_time,
            "is_suspicious": r.CouponLog.is_suspicious,
            "suspicious_reason": r.CouponLog.suspicious_reason,
            "user_agent": r.CouponLog.user_agent,
        }
        for r in rows
    ]


def retire(
    db: Session,
    code: str,
    account: Account,
    user_agent: Optional[str],
    reason: str,
) -> dict:
    """Atomické vyřazení kuponu. Terminální stav — nelze vrátit."""
    coupon = db.get(Coupon, code)
    if coupon is None:
        raise HTTPException(status_code=404, detail="Kupon nenalezen")
    if coupon.state == CouponState.VYRAZENA:
        raise HTTPException(
            status_code=409,
            detail={"message": "Kupon je již vyřazen", "current_state": "VYRAZENA"},
        )

    result = db.execute(
        text(
            "UPDATE coupons SET state='VYRAZENA', retired_reason=:reason, updated_at=now() "
            "WHERE code=:code AND state != 'VYRAZENA'"
        ),
        {"reason": reason, "code": code},
    )
    if result.rowcount == 0:
        # Race condition — jiný request vyřadil kupon mezitím
        raise HTTPException(
            status_code=409,
            detail={"message": "Kupon je již vyřazen", "current_state": "VYRAZENA"},
        )

    write_log(
        db,
        coupon_code=code,
        account=account,
        action=LogAction.VYRAZENI,
        result=LogResult.OK,
        user_agent=user_agent,
    )
    db.commit()
    return {"code": code, "state": CouponState.VYRAZENA.value}


def import_csv(db: Session, content: bytes, account: Account) -> dict:
    """Hromadný import kódů z CSV. Sloupec 'code' je povinný."""
    try:
        text_content = content.decode("utf-8-sig")  # zvládne i BOM z Excelu
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="CSV musí být v kódování UTF-8")

    reader = csv.DictReader(io.StringIO(text_content))
    rows = list(reader)

    if not reader.fieldnames or "code" not in reader.fieldnames:
        raise HTTPException(status_code=422, detail="CSV musí obsahovat sloupec 'code'")

    added = 0
    skipped = 0

    for row in rows:
        code = (row.get("code") or "").strip()
        if not code:
            skipped += 1
            continue

        if db.get(Coupon, code) is not None:
            skipped += 1
            continue

        db.add(Coupon(code=code, state=CouponState.VOLNA))
        write_log(
            db,
            coupon_code=code,
            account=account,
            action=LogAction.IMPORT,
            result=LogResult.OK,
            user_agent=None,
        )
        added += 1

    db.commit()
    return {"added": added, "skipped": skipped}
