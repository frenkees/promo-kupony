from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import require_role
from app.database import get_db
from app.models import Account, CouponLog, Restaurant
from app.schemas import RestaurantCreate, RestaurantResponse, RestaurantUpdate

router = APIRouter(tags=["restaurants"])


@router.get("/restaurants", response_model=list[RestaurantResponse])
def list_restaurants(
    db: Session = Depends(get_db),
    _account=Depends(require_role("manager")),
):
    return db.scalars(select(Restaurant).order_by(Restaurant.name)).all()


@router.post("/restaurants", response_model=RestaurantResponse, status_code=201)
def create_restaurant(
    body: RestaurantCreate,
    db: Session = Depends(get_db),
    _account=Depends(require_role("master")),
):
    r = Restaurant(name=body.name)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.put("/restaurants/{restaurant_id}", response_model=RestaurantResponse)
def update_restaurant(
    restaurant_id: int,
    body: RestaurantUpdate,
    db: Session = Depends(get_db),
    _account=Depends(require_role("master")),
):
    r = db.get(Restaurant, restaurant_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Pobočka nenalezena")
    r.name = body.name
    db.commit()
    db.refresh(r)
    return r


@router.delete("/restaurants/{restaurant_id}")
def delete_restaurant(
    restaurant_id: int,
    db: Session = Depends(get_db),
    _account=Depends(require_role("master")),
):
    r = db.get(Restaurant, restaurant_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Pobočka nenalezena")

    linked_accounts = db.scalar(
        select(func.count()).where(Account.restaurant_id == restaurant_id)
    ) or 0
    if linked_accounts > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Pobočka má {linked_accounts} vázaný/ch účtů, nelze smazat",
        )

    linked_logs = db.scalar(
        select(func.count()).where(CouponLog.restaurant_id == restaurant_id)
    ) or 0
    if linked_logs > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Pobočka má {linked_logs} záznamů v logu, nelze smazat",
        )

    db.delete(r)
    db.commit()
    return {"ok": True}
