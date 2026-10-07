from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_order_or_404
from app.database import get_db
from app.models.models import BomLine, Dish, Ingredient

router = APIRouter(prefix="/bom", tags=["bom"])


class BomLineUpdate(BaseModel):
    qty_per_portion: float


def _line_dict(r: BomLine, dishes: dict, ings: dict) -> dict:
    return {"id": r.id, "order_id": r.order_id, "dish_id": r.dish_id,
            "dish_name": dishes[r.dish_id].name,
            "ingredient_id": r.ingredient_id, "ingredient_name": ings[r.ingredient_id].name,
            "qty_per_portion": r.qty_per_portion, "unit": ings[r.ingredient_id].unit}


@router.get("")
def list_bom(order_id: int = Query(...), db: Session = Depends(get_db)):
    """本单定额行(平铺)。"""
    get_order_or_404(db, order_id)
    dishes = {d.id: d for d in db.scalars(select(Dish)).all()}
    ings = {i.id: i for i in db.scalars(select(Ingredient)).all()}
    rows = db.scalars(
        select(BomLine).where(BomLine.order_id == order_id).order_by(BomLine.dish_id, BomLine.id)
    ).all()
    return [_line_dict(r, dishes, ings) for r in rows]


@router.get("/tree")
def bom_tree(order_id: int = Query(...), db: Session = Depends(get_db)):
    """本单定额树:菜品挂在当前订单域下,别单的定额不进这棵树。"""
    get_order_or_404(db, order_id)
    dishes = db.scalars(select(Dish).order_by(Dish.id)).all()
    ings = {i.id: i for i in db.scalars(select(Ingredient)).all()}
    lines = db.scalars(select(BomLine).where(BomLine.order_id == order_id)).all()
    tree = []
    for d in dishes:
        children = [{"line_id": l.id, "ingredient_id": l.ingredient_id,
                     "ingredient": ings[l.ingredient_id].name, "qty": l.qty_per_portion,
                     "unit": ings[l.ingredient_id].unit}
                    for l in lines if l.dish_id == d.id]
        tree.append({"dish_id": d.id, "dish": d.name, "code": d.code, "children": children})
    return tree


@router.put("/{line_id}")
def update_bom_line(line_id: int, payload: BomLineUpdate,
                    order_id: int = Query(...), db: Session = Depends(get_db)):
    """改定额:只改当前订单名下的那一行;拿别单的行号来改,直接 404。"""
    get_order_or_404(db, order_id)
    line = db.get(BomLine, line_id)
    if not line or line.order_id != order_id:
        raise HTTPException(404, "定额行不存在或不属于当前订单")
    if payload.qty_per_portion < 0:
        raise HTTPException(400, "定额不能为负")
    line.qty_per_portion = payload.qty_per_portion
    db.commit()
    dishes = {d.id: d for d in db.scalars(select(Dish)).all()}
    ings = {i.id: i for i in db.scalars(select(Ingredient)).all()}
    return _line_dict(line, dishes, ings)
