from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect

from app.api.router import api_router
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.services.seed import seed_if_empty


def _schema_outdated() -> bool:
    """旧快照没有 bom_lines.order_id / prep_runs.status,结构漂移时重建(演示库只含种子数据)。"""
    insp = inspect(engine)
    if not insp.has_table("bom_lines"):
        return False
    bom_cols = {c["name"] for c in insp.get_columns("bom_lines")}
    run_cols = {c["name"] for c in insp.get_columns("prep_runs")}
    return "order_id" not in bom_cols or "status" not in run_cols


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if _schema_outdated():
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    if settings.seed_on_empty:
        db = SessionLocal()
        try:
            seed_if_empty(db)
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
