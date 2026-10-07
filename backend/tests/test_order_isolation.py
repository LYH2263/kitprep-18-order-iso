"""多订单域隔离测试：
A 单上改定额/生成/看缺料/作废，B 单的备料单、缺料贴、占用列一律不变；
库存结存永远停在生成前；跨单操作被拒；未作废备料单引用的出品删不掉且整体回退。
"""
import json

from sqlalchemy import select

from app.models.models import BomLine, OrderBomOverride, PrepRun


# ---------- 写入口必须显式带当前订单 ----------

def test_order_id_required(client, world):
    r = client.post("/api/prep/run")
    assert r.status_code == 422
    r = client.get("/api/prep/latest")
    assert r.status_code == 422
    r = client.get("/api/prep/shortages")
    assert r.status_code == 422
    r = client.get("/api/bom/tree")
    assert r.status_code == 422
    r = client.get("/api/inventory")
    assert r.status_code == 422
    r = client.put("/api/bom/override", json={"dish_id": 1, "ingredient_id": 1, "qty_per_portion": 1})
    assert r.status_code == 422


def test_unknown_order_404(client, world):
    assert client.post("/api/prep/run", params={"order_id": 999}).status_code == 404
    assert client.get("/api/inventory", params={"order_id": 999}).status_code == 404


# ---------- 改定额只在本单 ----------

def test_override_isolated_to_order(client, db_session, world):
    a, b, d1, i1 = world["a"], world["b"], world["d1"], world["i1"]
    r = client.put("/api/bom/override", params={"order_id": a},
                   json={"dish_id": d1, "ingredient_id": i1, "qty_per_portion": 0.9})
    assert r.status_code == 200

    # 全局基准 BOM 没动
    base = db_session.scalars(select(BomLine)).all()
    assert [(x.dish_id, x.ingredient_id, x.qty_per_portion) for x in base if x.dish_id == d1 and x.ingredient_id == i1] == [(d1, i1, 0.2)]

    # A 单树显示覆盖值并打标
    tree_a = client.get("/api/bom/tree", params={"order_id": a}).json()["tree"]
    node_a = next(n for n in tree_a if n["dish_id"] == d1)
    child_a = next(c for c in node_a["children"] if c["ingredient_id"] == i1)
    assert child_a["qty"] == 0.9 and child_a["overridden"] is True and child_a["base_qty"] == 0.2

    # B 单树仍是基准、未打标
    tree_b = client.get("/api/bom/tree", params={"order_id": b}).json()["tree"]
    node_b = next(n for n in tree_b if n["dish_id"] == d1)
    child_b = next(c for c in node_b["children"] if c["ingredient_id"] == i1)
    assert child_b["qty"] == 0.2 and child_b["overridden"] is False

    # 只存在 A 的一行覆盖
    ovs = db_session.scalars(select(OrderBomOverride)).all()
    assert [(o.order_id, o.qty_per_portion) for o in ovs] == [(a, 0.9)]

    # 重置 A 的覆盖，B 不受影响，基准还在
    r = client.request("DELETE", "/api/bom/override",
                       params={"order_id": a, "dish_id": d1, "ingredient_id": i1})
    assert r.status_code == 200
    again = client.get("/api/bom/tree", params={"order_id": a}).json()["tree"]
    c = next(c for n in again if n["dish_id"] == d1 for c in n["children"] if c["ingredient_id"] == i1)
    assert c["qty"] == 0.2 and c["overridden"] is False
    assert db_session.scalars(select(BomLine)).all()[0].qty_per_portion == 0.2


# ---------- 生成备料单只锁本单，结存不变 ----------

def test_run_locks_only_current_order(client, db_session, world):
    a, b, d1, i1 = world["a"], world["b"], world["d1"], world["i1"]
    # A 改定额为 0.9：需求 10*0.9=9.0，缺料 8.0
    client.put("/api/bom/override", params={"order_id": a},
               json={"dish_id": d1, "ingredient_id": i1, "qty_per_portion": 0.9})


    run_a = client.post("/api/prep/run", params={"order_id": a}).json()
    assert run_a["order"]["id"] == a
    line = next(l for l in run_a["prep_lines"] if l["ingredient_id"] == i1)
    assert line["need_qty"] == 9.0 and line["shortage"] == 8.0 and line["stock_qty"] == 1.0

    # B 单：无备料单时 latest 不再自动生成，缺料贴为空
    latest_b = client.get("/api/prep/latest", params={"order_id": b}).json()
    assert latest_b["id"] is None and latest_b["prep_lines"] == []
    sh_b = client.get("/api/prep/shortages", params={"order_id": b}).json()
    assert sh_b["shortages"] == [] and sh_b["stats"]["shortage_count"] == 0

    # 给 B 也生成一张：需求 5*0.2=1.0，无缺料
    run_b = client.post("/api/prep/run", params={"order_id": b}).json()
    line_b = next(l for l in run_b["prep_lines"] if l["ingredient_id"] == i1)
    assert line_b["need_qty"] == 1.0 and line_b["shortage"] == 0.0

    # A 的备料单/缺料贴没被 B 的操作改动
    latest_a = client.get("/api/prep/latest", params={"order_id": a}).json()
    assert latest_a["id"] == run_a["id"]
    la = next(l for l in latest_a["prep_lines"] if l["ingredient_id"] == i1)
    assert la["need_qty"] == 9.0 and la["shortage"] == 8.0
    sh_a = client.get("/api/prep/shortages", params={"order_id": a}).json()
    assert [s["shortage"] for s in sh_a["shortages"]] == [8.0]

    # 库存结存保持生成前（1.0），占用列各自独立
    inv_a = {x["id"]: x for x in client.get("/api/inventory", params={"order_id": a}).json()}
    inv_b = {x["id"]: x for x in client.get("/api/inventory", params={"order_id": b}).json()}
    assert inv_a[i1]["stock_qty"] == 1.0
    assert inv_b[i1]["stock_qty"] == 1.0
    assert inv_a[i1]["occupied_qty"] == 9.0 and inv_a[i1]["available_qty"] == -8.0
    assert inv_b[i1]["occupied_qty"] == 1.0 and inv_b[i1]["available_qty"] == 0.0

    # 备料单行只属于各自订单
    runs = db_session.scalars(select(PrepRun).order_by(PrepRun.id)).all()
    assert [(r.order_id, r.status) for r in runs] == [(a, "active"), (b, "active")]


def test_regenerate_voids_only_same_order(client, world):
    a, b = world["a"], world["b"]
    first_a = client.post("/api/prep/run", params={"order_id": a}).json()
    run_b = client.post("/api/prep/run", params={"order_id": b}).json()
    second_a = client.post("/api/prep/run", params={"order_id": a}).json()
    assert second_a["id"] != first_a["id"]

    # B 单单据仍 active，A 旧单已作废、新单 active
    sh_b = client.get("/api/prep/shortages", params={"order_id": b}).json()
    assert sh_b["run_id"] == run_b["id"]
    sh_a = client.get("/api/prep/shortages", params={"order_id": a}).json()
    assert sh_a["run_id"] == second_a["id"]

    # 重新生成不重复占用：A 的旧单已作废，占用只按新单 10*0.2=2.0
    inv_a2 = {x["id"]: x for x in client.get("/api/inventory", params={"order_id": a}).json()}
    assert inv_a2[world["i1"]]["occupied_qty"] == 2.0
    assert inv_a2[world["i1"]]["stock_qty"] == 1.0

    # 作废 A 新单不影响 B；跨单作废被拒
    r = client.post(f"/api/prep/{run_b['id']}/void", params={"order_id": a})
    assert r.status_code == 409
    r = client.post(f"/api/prep/{second_a['id']}/void", params={"order_id": a})
    assert r.status_code == 200 and r.json()["status"] == "void"
    assert client.post(f"/api/prep/{run_b['id']}/void", params={"order_id": b}).json()["status"] == "void"
    assert client.get("/api/prep/shortages", params={"order_id": a}).json()["shortages"] == []
    assert client.get("/api/prep/shortages", params={"order_id": b}).json()["shortages"] == []
    inv = {x["id"]: x for x in client.get("/api/inventory", params={"order_id": b}).json()}
    assert inv[world["i1"]]["occupied_qty"] == 0.0 and inv[world["i1"]]["stock_qty"] == 1.0


# ---------- 删除出品保护与整体回退 ----------

def test_delete_dish_blocked_and_rolled_back(client, db_session, world):
    a, b, d1, d2, i1 = world["a"], world["b"], world["d1"], world["d2"], world["i1"]
    client.post("/api/prep/run", params={"order_id": a})

    # d1 被 A 的未作废备料单用到：删除必须失败（即便从 B 单上下文发起也一样，保护是跨单的）
    r = client.delete(f"/api/dishes/{d1}")
    assert r.status_code == 409

    # 单还在、树还在、订单行还在（"单和树都退回"）
    from app.models.models import Dish, OrderLine
    assert db_session.get(Dish, d1) is not None
    assert len(db_session.scalars(select(OrderLine).where(OrderLine.dish_id == d1)).all()) == 2
    assert len(db_session.scalars(select(BomLine).where(BomLine.dish_id == d1)).all()) == 1
    # A 的备料单快照内容没被破坏
    run = db_session.scalars(select(PrepRun).where(PrepRun.order_id == a)).first()
    data = json.loads(run.result_json)
    assert data["dishes"] == [d1]
    assert any(l["ingredient_id"] == i1 for l in data["prep_lines"])

    # d2 没被任何单据使用，可以删，删除是原子提交
    assert client.delete(f"/api/dishes/{d2}").status_code == 200
    assert client.delete(f"/api/dishes/{d2}").status_code == 404

    # A 单据作废后 d1 才能删
    run_a = client.get("/api/prep/shortages", params={"order_id": a}).json()["run_id"]
    client.post(f"/api/prep/{run_a}/void", params={"order_id": a})
    assert client.delete(f"/api/dishes/{d1}").status_code == 200
    assert db_session.scalars(select(OrderBomOverride)).all() == []
