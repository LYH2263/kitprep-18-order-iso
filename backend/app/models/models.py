from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Dish(Base):
    __tablename__ = "dishes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    portion_unit: Mapped[str] = mapped_column(String(16), default="份")

class Ingredient(Base):
    __tablename__ = "ingredients"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    unit: Mapped[str] = mapped_column(String(16), default="kg")
    stock_qty: Mapped[float] = mapped_column(Float, default=0.0)

class BomLine(Base):
    """全局基准定额（生产厨房口径）。"""
    __tablename__ = "bom_lines"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id"))
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"))
    qty_per_portion: Mapped[float] = mapped_column(Float)

class KitchenOrder(Base):
    __tablename__ = "kitchen_orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    outlet: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="open")

class OrderLine(Base):
    __tablename__ = "order_lines"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("kitchen_orders.id"))
    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id"))
    portions: Mapped[int] = mapped_column(Integer)

class OrderBomOverride(Base):
    """订单级定额覆盖：只在本订单的定额树/备料展开中生效，绝不动全局 BOM 与其它订单。"""
    __tablename__ = "order_bom_overrides"
    __table_args__ = (UniqueConstraint("order_id", "dish_id", "ingredient_id", name="uq_order_bom_override"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("kitchen_orders.id"))
    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id"))
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"))
    qty_per_portion: Mapped[float] = mapped_column(Float)

class PrepRun(Base):
    """一张订单的备料单快照。status=active 时占用库存、锁定出品删除；void=已作废。"""
    __tablename__ = "prep_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("kitchen_orders.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(16), default="active")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
