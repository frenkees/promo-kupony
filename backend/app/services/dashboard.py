from datetime import datetime
from typing import Optional

from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.orm import Session

from app.models import Account, Coupon, CouponLog, CouponState, LogAction, Restaurant


def _period_where(date_from: Optional[datetime], date_to: Optional[datetime]) -> list:
    """Vrátí seznam WHERE podmínek pro filtrování coupon_logs dle časového rozsahu."""
    filters = []
    if date_from:
        filters.append(CouponLog.server_time >= date_from)
    if date_to:
        filters.append(CouponLog.server_time < date_to)
    return filters


def overview(
    db: Session,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> dict:
    """Přehledový dashboard pro manažera."""
    # Aktuální počet nevyplacených závazků
    open_liability: int = db.scalar(
        select(func.count()).select_from(Coupon).where(Coupon.state == CouponState.K_UPLATNENI)
    ) or 0

    # Fond: počty dle stavu
    fund: dict[str, int] = {
        state.value: (
            db.scalar(select(func.count()).select_from(Coupon).where(Coupon.state == state)) or 0
        )
        for state in CouponState
    }

    # Statistiky za zvolené období
    pf = _period_where(date_from, date_to)

    issued_count: int = db.scalar(
        select(func.count()).select_from(CouponLog)
        .where(CouponLog.action == LogAction.VYDANI, *pf)
    ) or 0

    redeemed_count: int = db.scalar(
        select(func.count()).select_from(CouponLog)
        .where(CouponLog.action == LogAction.UPLATNENI, *pf)
    ) or 0

    redemption_rate = round(redeemed_count / issued_count, 4) if issued_count else 0.0

    # Statistiky dle pobočky (JOIN podmínka obsahuje period filter, aby LEFT JOIN fungoval správně)
    join_cond = and_(CouponLog.restaurant_id == Restaurant.id, *pf)

    rows = db.execute(
        select(
            Restaurant.id.label("restaurant_id"),
            Restaurant.name,
            func.sum(case((CouponLog.action == LogAction.VYDANI, 1), else_=0)).label("issued"),
            func.sum(case((CouponLog.action == LogAction.UPLATNENI, 1), else_=0)).label("redeemed"),
        )
        .select_from(Restaurant)
        .outerjoin(CouponLog, join_cond)
        .group_by(Restaurant.id, Restaurant.name)
        .order_by(Restaurant.name)
    ).all()

    by_restaurant = [
        {
            "restaurant_id": r.restaurant_id,
            "name": r.name,
            "issued": r.issued or 0,
            "redeemed": r.redeemed or 0,
        }
        for r in rows
    ]

    return {
        "open_liability": open_liability,
        "redemption_rate": redemption_rate,
        "fund": fund,
        "by_restaurant": by_restaurant,
    }


def suspicious(
    db: Session,
    restaurant_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> list[dict]:
    """Seznam podezřelých akcí s volitelným filtrem pobočky a období."""
    stmt = (
        select(
            CouponLog,
            Account.login.label("account_login"),
            Restaurant.name.label("restaurant_name"),
        )
        .join(Account, CouponLog.account_id == Account.id)
        .outerjoin(Restaurant, CouponLog.restaurant_id == Restaurant.id)
        .where(CouponLog.is_suspicious == True)  # noqa: E712
        .order_by(desc(CouponLog.server_time))
    )

    if restaurant_id is not None:
        stmt = stmt.where(CouponLog.restaurant_id == restaurant_id)
    if date_from is not None:
        stmt = stmt.where(CouponLog.server_time >= date_from)
    if date_to is not None:
        stmt = stmt.where(CouponLog.server_time < date_to)

    rows = db.execute(stmt).all()
    return [
        {
            "id": r.CouponLog.id,
            "coupon_code": r.CouponLog.coupon_code,
            "action": r.CouponLog.action.value,
            "result": r.CouponLog.result.value,
            "account_login": r.account_login,
            "restaurant_name": r.restaurant_name,
            "server_time": r.CouponLog.server_time,
            "suspicious_reason": r.CouponLog.suspicious_reason,
            "user_agent": r.CouponLog.user_agent,
        }
        for r in rows
    ]
