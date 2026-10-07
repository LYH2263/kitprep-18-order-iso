import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import BomLine, Dish, OrderBomOverride, OrderLine, PrepRun
router = APIRouter(prefix="/dishes", tags=["dishes"])

@router.get("")
def list_dishes(db: Session = Depends(get_db)):
    return [{"id": r.id, "code": r.code, "name": r.name, "portion_unit": r.portion_unit}
            for r in db.scalars(select(Dish).order_by(Dish.id)).all()]

def _used_by_active_run(dish_id: int, db: Session) -> int | None:
    """返回第一张用到该出品的未作废备料单 id（跨所有订单），没有则 None。"""
    runs = db.scalars(select(PrepRun).where(PrepRun.status == "active")).all()
    for run in runs:
        if dish_id in json.loads(run.result_json).get("dishes", []):
            return run.id
    return None

@router.delete("/{dish_id}")
def delete_dish(dish_id: int, db: Session = Depends(get_db)):
    """删除出品：只要任一订单存在用到它的未作废备料单就整体失败，
    备料单、定额树、订单行全部回退，不允许删一半。不做领料出库之类的旁路。"""
    dish = db.get(Dish, dish_id)
    if not dish:
        raise HTTPException(404, "出品不存在")
    run_id = _used_by_active_run(dish_id, db)
    if run_id is not None:
        raise HTTPException(409, f"出品已被未作废备料单 #{run_id} 用到，不能删除；请先作废该备料单")
    try:
        for ol in db.scalars(select(OrderLine).where(OrderLine.dish_id == dish_id)).all():
            db.delete(ol)
        for ov in db.scalars(select(OrderBomOverride).where(OrderBomOverride.dish_id == dish_id)).all():
            db.delete(ov)
        for bl in db.scalars(select(BomLine).where(BomLine.dish_id == dish_id)).all():
            db.delete(bl)
        db.delete(dish)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"id": dish_id, "deleted": True}
