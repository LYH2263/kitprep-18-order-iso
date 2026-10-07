from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import BomLine, Dish, Ingredient, KitchenOrder, OrderBomOverride

router = APIRouter(prefix="/bom", tags=["bom"])

def _get_order(order_id: int, db: Session) -> KitchenOrder:
    order = db.get(KitchenOrder, order_id)
    if not order:
        raise HTTPException(404, "订单不存在")
    return order

def _effective_map(order_id: int, db: Session) -> dict[tuple[int, int], float]:
    """本单生效定额 = 全局基准 BOM，被 (order_id, dish, ingredient) 覆盖逐格替换。"""
    eff = {(b.dish_id, b.ingredient_id): b.qty_per_portion
           for b in db.scalars(select(BomLine)).all()}
    overrides = db.scalars(select(OrderBomOverride).where(OrderBomOverride.order_id == order_id)).all()
    for o in overrides:
        eff[(o.dish_id, o.ingredient_id)] = o.qty_per_portion
    return eff

def _override_keys(order_id: int, db: Session) -> set[tuple[int, int]]:
    return {(o.dish_id, o.ingredient_id)
            for o in db.scalars(select(OrderBomOverride).where(OrderBomOverride.order_id == order_id)).all()}

@router.get("")
def list_bom(order_id: int, db: Session = Depends(get_db)):
    """当前订单生效定额明细（基准 + 本单覆盖），带 overridden 标记。"""
    _get_order(order_id, db)
    dishes = {d.id: d for d in db.scalars(select(Dish)).all()}
    ings = {i.id: i for i in db.scalars(select(Ingredient)).all()}
    base = {(b.dish_id, b.ingredient_id): b.qty_per_portion
            for b in db.scalars(select(BomLine)).all()}
    eff = _effective_map(order_id, db)
    overridden = _override_keys(order_id, db)
    rows = []
    for (dish_id, ingredient_id), qty in sorted(eff.items()):
        rows.append({
            "dish_id": dish_id, "dish_name": dishes[dish_id].name,
            "ingredient_id": ingredient_id, "ingredient_name": ings[ingredient_id].name,
            "qty_per_portion": qty, "base_qty_per_portion": base.get((dish_id, ingredient_id)),
            "overridden": (dish_id, ingredient_id) in overridden,
            "unit": ings[ingredient_id].unit,
        })
    return rows

@router.get("/tree")
def bom_tree(order_id: int, db: Session = Depends(get_db)):
    """当前订单定额树：只在本单生效的定额，覆盖格高亮，绝不显示/改动别单覆盖。"""
    order = _get_order(order_id, db)
    dishes = db.scalars(select(Dish).order_by(Dish.id)).all()
    ings = {i.id: i for i in db.scalars(select(Ingredient)).all()}
    base = {(b.dish_id, b.ingredient_id): b.qty_per_portion
            for b in db.scalars(select(BomLine)).all()}
    eff = _effective_map(order_id, db)
    overridden = _override_keys(order_id, db)
    tree = []
    for d in dishes:
        children = [{
            "ingredient_id": iid,
            "ingredient": ings[iid].name,
            "qty": qty,
            "base_qty": base.get((d.id, iid)),
            "overridden": (d.id, iid) in overridden,
            "unit": ings[iid].unit,
        } for (did, iid), qty in sorted(eff.items()) if did == d.id]
        tree.append({"dish": d.name, "code": d.code, "dish_id": d.id, "children": children})
    return {"order": {"id": order.id, "code": order.code, "outlet": order.outlet}, "tree": tree}

class OverrideIn(BaseModel):
    dish_id: int
    ingredient_id: int
    qty_per_portion: float = Field(ge=0)

@router.put("/override")
def put_override(order_id: int, body: OverrideIn, db: Session = Depends(get_db)):
    """改定额：只写当前订单的覆盖格。全局基准 BOM 与其它订单的树原样不动，单事务原子提交。"""
    _get_order(order_id, db)
    base = db.scalars(
        select(BomLine).where(BomLine.dish_id == body.dish_id,
                              BomLine.ingredient_id == body.ingredient_id)
    ).first()
    if not base:
        raise HTTPException(404, "该菜品 BOM 下没有此原料，不能新增定额")
    if not db.get(Dish, body.dish_id) or not db.get(Ingredient, body.ingredient_id):
        raise HTTPException(404, "菜品或原料不存在")
    try:
        ov = db.scalars(
            select(OrderBomOverride).where(OrderBomOverride.order_id == order_id,
                                           OrderBomOverride.dish_id == body.dish_id,
                                           OrderBomOverride.ingredient_id == body.ingredient_id)
        ).first()
        if ov:
            ov.qty_per_portion = body.qty_per_portion
        else:
            db.add(OrderBomOverride(order_id=order_id, dish_id=body.dish_id,
                                    ingredient_id=body.ingredient_id,
                                    qty_per_portion=body.qty_per_portion))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"order_id": order_id, "dish_id": body.dish_id,
            "ingredient_id": body.ingredient_id, "qty_per_portion": body.qty_per_portion}

@router.delete("/override")
def delete_override(order_id: int, dish_id: int, ingredient_id: int, db: Session = Depends(get_db)):
    """定额恢复基准：只删当前订单的覆盖；其它订单覆盖与基准 BOM 不允许被碰到。"""
    _get_order(order_id, db)
    ov = db.scalars(
        select(OrderBomOverride).where(OrderBomOverride.order_id == order_id,
                                       OrderBomOverride.dish_id == dish_id,
                                       OrderBomOverride.ingredient_id == ingredient_id)
    ).first()
    if not ov:
        raise HTTPException(404, "当前订单没有该定额覆盖")
    db.delete(ov)
    db.commit()
    return {"order_id": order_id, "dish_id": dish_id, "ingredient_id": ingredient_id, "reset": True}
