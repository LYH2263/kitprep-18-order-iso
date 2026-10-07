import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.models import (
    BomLine, Dish, Ingredient, KitchenOrder, OrderBomOverride, OrderLine, PrepRun,
)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = TestingSession()

    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield db
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    return TestClient(app)


@pytest.fixture()
def world(db_session):
    """两张订单：A(1) 含 D1 10份；B(2) 含 D1 5份。D1 每份用 I1 0.2，库存 1.0。"""
    db = db_session
    d1 = Dish(code="D1", name="红烧", portion_unit="份")
    d2 = Dish(code="D2", name="青菜", portion_unit="份")
    db.add_all([d1, d2]); db.flush()
    i1 = Ingredient(code="I1", name="肉", unit="kg", stock_qty=1.0)
    db.add(i1); db.flush()
    db.add(BomLine(dish_id=d1.id, ingredient_id=i1.id, qty_per_portion=0.2))
    db.add(BomLine(dish_id=d2.id, ingredient_id=i1.id, qty_per_portion=0.5))
    a = KitchenOrder(code="A", outlet="城西", status="open")
    b = KitchenOrder(code="B", status="open", outlet="城东")
    db.add_all([a, b]); db.flush()
    db.add(OrderLine(order_id=a.id, dish_id=d1.id, portions=10))
    db.add(OrderLine(order_id=b.id, dish_id=d1.id, portions=5))
    db.commit()
    return {"a": a.id, "b": b.id, "d1": d1.id, "d2": d2.id, "i1": i1.id}
