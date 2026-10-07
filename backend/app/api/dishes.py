from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import VOIDED
from app.database import get_db
from app.models.models import BomLine, Dish, OrderLine, PrepRun

router = APIRouter(prefix="/dishes", tags=["dishes"])


@router.get("")
def list_dishes(db: Session = Depends(get_db)):
    return [{"id": r.id, "code": r.code, "name": r.name, "portion_unit": r.portion_unit}
            for r in db.scalars(select(Dish).order_by(Dish.id)).all()]


@router.delete("/{dish_id}")
def delete_dish(dish_id: int, db: Session = Depends(get_db)):
    """删除出品。

    任一未作废备料单(不论哪张订单)用到该出品 → 409,什么都不删;
    允许删除时,订单行、定额树、出品在同一事务里一起删,失败整体回滚。
    """
    dish = db.get(Dish, dish_id)
    if not dish:
        raise HTTPException(404, "出品不存在")
    used = db.scalars(
        select(PrepRun.id)
        .join(OrderLine, OrderLine.order_id == PrepRun.order_id)
        .where(PrepRun.status != VOIDED, OrderLine.dish_id == dish_id)
        .limit(1)
    ).first()
    if used is not None:
        raise HTTPException(409, "该出品已被未作废备料单使用,不能删除")
    db.execute(delete(OrderLine).where(OrderLine.dish_id == dish_id))
    db.execute(delete(BomLine).where(BomLine.dish_id == dish_id))
    db.delete(dish)
    db.commit()
    return {"deleted": dish_id}
