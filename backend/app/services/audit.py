import re
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Account, CouponLog, LogAction, LogResult

PRAGUE = ZoneInfo("Europe/Prague")


def _normalize_ua(ua: Optional[str]) -> str:
    """Odstraní VŠECHNY číslice a tečky z UA (i z OS identifikátorů).

    Záměrně jednoduché: 'Chrome 124' a 'Chrome 125' kolabnou na totéž,
    ale 'Chrome' a 'Firefox' ne. NEDĚLAT nic chytřejšího.
    """
    if not ua:
        return ""
    return re.sub(r"[\d.]+", "", ua).strip()


def _is_night_time(dt_utc: datetime, start: int, end: int) -> bool:
    """Vrátí True pokud hodina v Praze spadá do nočního okna."""
    hour = dt_utc.astimezone(PRAGUE).hour
    if start <= end:
        return start <= hour < end
    # Přes půlnoc, např. 22–6
    return hour >= start or hour < end


def write_log(
    db: Session,
    *,
    coupon_code: str,
    account: Account,
    action: LogAction,
    result: LogResult,
    user_agent: Optional[str],
    bypass_reason: Optional[str] = None,
) -> CouponLog:
    """Vytvoří záznam v coupon_logs a vyhodnotí heuristiky podezřelosti.

    Volat uvnitř otevřené transakce — commit provádí volající.
    """
    server_time = datetime.now(timezone.utc)
    reasons: list[str] = []

    # Bypass — důvod zadaný operátorem je vždy první
    if bypass_reason:
        reasons.append(bypass_reason)

    # Odlišné zařízení od baseline — porovnáváme normalizované UA (bez verzí)
    if (
        account.baseline_user_agent
        and user_agent
        and _normalize_ua(account.baseline_user_agent) != _normalize_ua(user_agent)
    ):
        reasons.append("odlišné zařízení")

    # Mimo provozní dobu
    if _is_night_time(server_time, settings.NIGHT_WINDOW_START, settings.NIGHT_WINDOW_END):
        reasons.append("mimo provozní dobu")

    log = CouponLog(
        coupon_code=coupon_code,
        account_id=account.id,
        restaurant_id=account.restaurant_id,
        action=action,
        result=result,
        is_suspicious=bool(reasons),
        suspicious_reason="; ".join(reasons) if reasons else None,
        server_time=server_time,
        user_agent=user_agent,
    )
    db.add(log)
    return log
