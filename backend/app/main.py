from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.database import SessionLocal
from app.limiter import limiter
from app.routers import auth as auth_module
from app.routers import coupons as coupons_module
from app.routers import accounts as accounts_module
from app.routers import dashboard as dashboard_module
from app.routers import restaurants as restaurants_module
from app.seed import seed_master


def run_migrations() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    with SessionLocal() as db:
        seed_master(db)
    yield


app = FastAPI(title="Promo Kupony API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth_module.router, prefix="/api")
app.include_router(coupons_module.router, prefix="/api")
app.include_router(dashboard_module.router, prefix="/api")
app.include_router(restaurants_module.router, prefix="/api")
app.include_router(accounts_module.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
