import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ACTIVE, VOIDED, active_run, get_order_or_404
from app.database import get_db
from app.models.models import BomLine, Dish, Ingredient, OrderLine, PrepRun
from app.services.bom_engine import explode_and_merge, result_to_dict

router = APIRouter(prefix="/prep", tags=["prep"])


def _run_payload(run: PrepRun) -> dict:
    return {
        "id": run.id,
        "status": run.status,
        "created_at": run.created_at.isoformat(),
        **json.loads(run.result_json),
    }


def _empty_payload(order) -> dict:
    return {
        "id": None,
        "status": None,
        "order": {"id": order.id, "code": order.code, "outlet": order.outlet},
        "order_lines": [],
        "prep_lines": [],
        "shortages": [],
        "stats": {"ingredient_count": 0, "shortage_count": 0, "total_shortage_qty": 0},
    }


@router.post("/run")
def run_prep(order_id: int = Query(...), db: Session = Depends(get_db)):
    """生成备料单:只锁本单。

    - 需求只按本单订单行 × 本单定额树展开;
    - 本单旧的生效备料单作废顶替,占用以新单为准(不翻倍);
    - 不写库存结存,不读写任何其他订单的数据。
    """
    order = get_order_or_404(db, order_id)
    ols = [{"dish_id": l.dish_id, "portions": l.portions}
           for l in db.scalars(select(OrderLine).where(OrderLine.order_id == order_id)).all()]
    bom = [{"dish_id": b.dish_id, "ingredient_id": b.ingredient_id, "qty_per_portion": b.qty_per_portion}
           for b in db.scalars(select(BomLine).where(BomLine.order_id == order_id)).all()]
    ings = {i.id: {"code": i.code, "name": i.name, "unit": i.unit, "stock_qty": i.stock_qty}
            for i in db.scalars(select(Ingredient)).all()}
    result = result_to_dict(explode_and_merge(ols, bom, ings))
    for line in result["prep_lines"]:
        line["occupied_qty"] = line["need_qty"]  # 占用 = 本单锁定需求;结存不动
    dishes = {d.id: d for d in db.scalars(select(Dish)).all()}
    result["order_lines"] = [
        {"dish_id": ol["dish_id"], "dish_name": dishes[ol["dish_id"]].name, "portions": ol["portions"]}
        for ol in ols
    ]
    result["order"] = {"id": order.id, "code": order.code, "outlet": order.outlet}
    # 顶替只发生在本单域内
    for old in db.scalars(
        select(PrepRun).where(PrepRun.order_id == order_id, PrepRun.status == ACTIVE)
    ).all():
        old.status = VOIDED
    run = PrepRun(order_id=order_id, created_at=datetime.utcnow(), status=ACTIVE,
                  result_json=json.dumps(result, ensure_ascii=False))
    db.add(run)
    db.commit()
    db.refresh(run)
    return _run_payload(run)


@router.get("/latest")
def latest(order_id: int = Query(...), db: Session = Depends(get_db)):
    """本单当前生效备料单;没有就返回空单,绝不顺手生成(读入口不写)。"""
    order = get_order_or_404(db, order_id)
    run = active_run(db, order_id)
    if not run:
        return _empty_payload(order)
    return _run_payload(run)


@router.get("/shortages")
def shortages(order_id: int = Query(...), db: Session = Depends(get_db)):
    """本单缺料贴,来自本单生效备料单快照。"""
    order = get_order_or_404(db, order_id)
    run = active_run(db, order_id)
    data = _run_payload(run) if run else _empty_payload(order)
    return {"order_id": order_id, "shortages": data.get("shortages", []), "stats": data.get("stats", {})}


@router.get("/runs")
def list_runs(order_id: int = Query(...), db: Session = Depends(get_db)):
    """本单备料单历史(含已作废)。"""
    get_order_or_404(db, order_id)
    runs = db.scalars(
        select(PrepRun).where(PrepRun.order_id == order_id).order_by(PrepRun.id.desc())
    ).all()
    return [
        {
            "id": r.id,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
            "stats": json.loads(r.result_json).get("stats", {}),
        }
        for r in runs
    ]


@router.post("/runs/{run_id}/void")
def void_run(run_id: int, order_id: int = Query(...), db: Session = Depends(get_db)):
    """作废本单的一张备料单,释放本单占用。跨单的备料单视为不存在。"""
    get_order_or_404(db, order_id)
    run = db.get(PrepRun, run_id)
    if not run or run.order_id != order_id:
        raise HTTPException(404, "备料单不存在或不属于当前订单")
    if run.status == VOIDED:
        raise HTTPException(409, "备料单已作废")
    run.status = VOIDED
    db.commit()
    return {"id": run.id, "status": run.status}
