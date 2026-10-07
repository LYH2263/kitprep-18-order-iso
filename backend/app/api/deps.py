"""订单域共享件:所有读写都必须先落到当前订单上。"""
import json

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import KitchenOrder, PrepRun

ACTIVE = "active"
VOIDED = "voided"


def get_order_or_404(db: Session, order_id: int) -> KitchenOrder:
    order = db.get(KitchenOrder, order_id)
    if not order:
        raise HTTPException(404, "订单不存在")
    return order


def active_run(db: Session, order_id: int) -> PrepRun | None:
    """本单当前生效的备料单(每单至多一张)。"""
    return db.scalars(
        select(PrepRun)
        .where(PrepRun.order_id == order_id, PrepRun.status == ACTIVE)
        .order_by(PrepRun.id.desc())
    ).first()


def occupied_map(db: Session, order_id: int) -> dict[int, float]:
    """本单占用:生效备料单锁定的原料数量。只看本单,绝不汇总他单。"""
    run = active_run(db, order_id)
    if not run:
        return {}
    data = json.loads(run.result_json)
    return {l["ingredient_id"]: l["need_qty"] for l in data.get("prep_lines", [])}
