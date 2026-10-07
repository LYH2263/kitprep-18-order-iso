import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import BomLine, Ingredient, KitchenOrder, OrderBomOverride, OrderLine, PrepRun
from app.services.bom_engine import apply_overrides, explode_and_merge, result_to_dict
router = APIRouter(prefix="/prep", tags=["prep"])

def _get_order(order_id: int, db: Session) -> KitchenOrder:
    order = db.get(KitchenOrder, order_id)
    if not order:
        raise HTTPException(404, "订单不存在")
    return order

def _explode(order_id: int, db: Session) -> dict:
    """按本单生效定额（基准 BOM + 本单覆盖）展开；只读取库存结存，绝不写库存。"""
    ols = [{"dish_id": l.dish_id, "portions": l.portions}
           for l in db.scalars(select(OrderLine).where(OrderLine.order_id == order_id)).all()]
    base = [{"dish_id": b.dish_id, "ingredient_id": b.ingredient_id, "qty_per_portion": b.qty_per_portion}
            for b in db.scalars(select(BomLine)).all()]
    overrides = [{"dish_id": o.dish_id, "ingredient_id": o.ingredient_id, "qty_per_portion": o.qty_per_portion}
                 for o in db.scalars(select(OrderBomOverride).where(OrderBomOverride.order_id == order_id)).all()]
    ings = {i.id: {"code": i.code, "name": i.name, "unit": i.unit, "stock_qty": i.stock_qty}
            for i in db.scalars(select(Ingredient)).all()}
    lines = explode_and_merge(ols, apply_overrides(base, overrides), ings)
    result = result_to_dict(lines, dish_ids=[l["dish_id"] for l in ols])
    return result

@router.post("/run")
def run_prep(order_id: int, db: Session = Depends(get_db)):
    """为当前订单生成备料单：只锁本单。同一订单内旧的未作废单据在同一事务里作废，
    绝不触碰其它订单的备料单、缺料贴、占用，也绝不改库存结存。"""
    order = _get_order(order_id, db)
    try:
        old = db.scalars(
            select(PrepRun).where(PrepRun.order_id == order_id, PrepRun.status == "active")
        ).all()
        for r in old:
            r.status = "void"
        result = _explode(order_id, db)
        result["order"] = {"id": order.id, "code": order.code, "outlet": order.outlet}
        run = PrepRun(order_id=order_id, status="active",
                      created_at=datetime.utcnow(),
                      result_json=json.dumps(result, ensure_ascii=False))
        db.add(run)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(run)
    return {"id": run.id, "status": run.status, **json.loads(run.result_json)}

@router.get("/latest")
def latest(order_id: int, db: Session = Depends(get_db)):
    """取当前订单最近一张备料单（含已作废）。不存在时不自动生成。"""
    order = _get_order(order_id, db)
    run = db.scalars(
        select(PrepRun).where(PrepRun.order_id == order_id).order_by(PrepRun.id.desc())
    ).first()
    if not run:
        return {"id": None, "status": None, "prep_lines": [], "shortages": [], "dishes": [],
                "stats": {"ingredient_count": 0, "shortage_count": 0, "total_shortage_qty": 0},
                "order": {"id": order.id, "code": order.code, "outlet": order.outlet}}
    return {"id": run.id, "status": run.status, **json.loads(run.result_json)}

@router.get("/shortages")
def shortages(order_id: int, db: Session = Depends(get_db)):
    """缺料贴只读本单最近一张未作废备料单的快照；本单没生成过就是空贴。"""
    _get_order(order_id, db)
    run = db.scalars(
        select(PrepRun).where(PrepRun.order_id == order_id, PrepRun.status == "active")
        .order_by(PrepRun.id.desc())
    ).first()
    if not run:
        return {"order_id": order_id, "shortages": [],
                "stats": {"ingredient_count": 0, "shortage_count": 0, "total_shortage_qty": 0}}
    data = json.loads(run.result_json)
    return {"order_id": order_id, "run_id": run.id,
            "shortages": data.get("shortages", []), "stats": data.get("stats", {})}

@router.post("/{run_id}/void")
def void_run(run_id: int, order_id: int, db: Session = Depends(get_db)):
    """作废备料单：单据必须属于当前订单，禁止跨单作废。"""
    _get_order(order_id, db)
    run = db.get(PrepRun, run_id)
    if not run:
        raise HTTPException(404, "备料单不存在")
    if run.order_id != order_id:
        raise HTTPException(409, "该备料单属于其它订单，禁止跨单作废")
    if run.status != "void":
        run.status = "void"
        db.commit()
    return {"id": run.id, "order_id": run.order_id, "status": run.status}
