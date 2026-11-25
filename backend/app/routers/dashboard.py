from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import require_role
from app.database import get_db
from app.models import Account
from app.schemas import DashboardOverview, SuspiciousEntry
from app.services import dashboard as dashboard_svc

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/overview", response_model=DashboardOverview)
def get_overview(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    account: Account = Depends(require_role("manager")),
):
    return dashboard_svc.overview(db, date_from=date_from, date_to=date_to)


@router.get("/dashboard/suspicious", response_model=list[SuspiciousEntry])
def get_suspicious(
    restaurant_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    account: Account = Depends(require_role("manager")),
):
    return dashboard_svc.suspicious(
        db,
        restaurant_id=restaurant_id,
        date_from=date_from,
        date_to=date_to,
    )
