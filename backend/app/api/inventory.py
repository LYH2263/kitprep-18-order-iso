import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Ingredient, KitchenOrder, PrepRun
router = APIRouter(prefix="/inventory", tags=["inventory"])

@router.get("")
def list_inventory(order_id: int, db: Session = Depends(get_db)):
    """结存 stock_qty 永远是生成备料单前的数字，任何备料单都不写它。
    occupied_qty 只统计当前订单未作废备料单的需求；可用 = 结存 − 本单占用。"""
    order = db.get(KitchenOrder, order_id)
    if not order:
        raise HTTPException(404, "订单不存在")
    runs = db.scalars(
        select(PrepRun).where(PrepRun.order_id == order_id, PrepRun.status == "active")
    ).all()
    occupied: dict[int, float] = {}
    for r in runs:
        for line in json.loads(r.result_json).get("prep_lines", []):
            iid = line["ingredient_id"]
            occupied[iid] = occupied.get(iid, 0.0) + float(line["need_qty"])
    rows = []
    for r in db.scalars(select(Ingredient).order_by(Ingredient.id)).all():
        occ = round(occupied.get(r.id, 0.0), 3)
        rows.append({"id": r.id, "code": r.code, "name": r.name, "unit": r.unit,
                     "stock_qty": r.stock_qty, "occupied_qty": occ,
                     "available_qty": round(r.stock_qty - occ, 3)})
    return rows
