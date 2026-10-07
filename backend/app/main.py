from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api.router import api_router
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.services.seed import ensure_demo_orders, seed_if_empty


def _ensure_schema() -> None:
    """轻量幂等迁移：create_all 不补已有表的新列，这里给旧库补齐。
    prep_runs.status 缺失时补列并把历史备料单视为生效中；
    order_bom_overrides 是新表，由 create_all 建立。"""
    Base.metadata.create_all(bind=engine)
    insp = inspect(engine)
    if "prep_runs" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("prep_runs")}
        if "status" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE prep_runs ADD COLUMN status VARCHAR(16) DEFAULT 'active'"))
                conn.execute(text("UPDATE prep_runs SET status = 'active' WHERE status IS NULL"))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _ensure_schema()
    if settings.seed_on_empty:
        db = SessionLocal()
        try:
            seed_if_empty(db)
            ensure_demo_orders(db)
        finally:
            db.close()
    yield


app = FastAPI(title="KitPrep", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api")
