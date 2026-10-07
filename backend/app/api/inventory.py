from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_order_or_404, occupied_map
from app.database import get_db
from app.models.models import Ingredient

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("")
def list_inventory(order_id: int | None = Query(None),
                   db: Session = Depends(get_db)):
    """结存 = stock_qty,生成备料单不动它;占用列只算当前订单。"""
    occupied = {}
    if order_id is not None:
        get_order_or_404(db, order_id)
        occupied = occupied_map(db, order_id)
    return [
        {
            "id": r.id,
            "code": r.code,
            "name": r.name,
            "unit": r.unit,
            "stock_qty": r.stock_qty,
            "occupied_qty": round(occupied.get(r.id, 0.0), 3),
        }
        for r in db.scalars(select(Ingredient).order_by(Ingredient.id)).all()
    ]
