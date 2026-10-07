"""订单域隔离测试:写入口带当前订单,对岸禁止被改。"""


def _orders(client):
    return client.get("/api/orders").json()


def _two_orders(client):
    orders = _orders(client)
    assert len(orders) >= 2, "种子里应有多张订单"
    return orders[0]["id"], orders[1]["id"]


def _tree(client, order_id):
    r = client.get("/api/bom/tree", params={"order_id": order_id})
    assert r.status_code == 200
    return r.json()


def _find_line(tree, dish_code, ingredient_name):
    for d in tree:
        if d["code"] == dish_code:
            for c in d["children"]:
                if c["ingredient"] == ingredient_name:
                    return c
    raise AssertionError(f"定额行不存在: {dish_code}/{ingredient_name}")


def _inv(client, order_id=None):
    params = {} if order_id is None else {"order_id": order_id}
    return {r["code"]: r for r in client.get("/api/inventory", params=params).json()}


def _latest(client, order_id):
    return client.get("/api/prep/latest", params={"order_id": order_id}).json()


def _shortages(client, order_id):
    return client.get("/api/prep/shortages", params={"order_id": order_id}).json()


def _run(client, order_id):
    r = client.post("/api/prep/run", params={"order_id": order_id})
    assert r.status_code == 200, r.text
    return r.json()


# ---------- 生成备料单:只锁本单 ----------

def test_generate_locks_only_current_order(client):
    o1, o2 = _two_orders(client)
    data = _run(client, o1)
    assert data["order"]["id"] == o1
    assert data["prep_lines"], "本单应有备料行"
    assert all(l["occupied_qty"] == l["need_qty"] for l in data["prep_lines"])

    # 对岸:没有备料单、没有缺料、占用为 0
    assert _latest(client, o2)["prep_lines"] == []
    assert _shortages(client, o2)["shortages"] == []
    assert all(r["occupied_qty"] == 0 for r in _inv(client, o2).values())
    # 本单占用已锁
    assert any(r["occupied_qty"] > 0 for r in _inv(client, o1).values())


def test_inventory_balance_unchanged_by_generate(client):
    o1, _ = _two_orders(client)
    before = {c: r["stock_qty"] for c, r in _inv(client).items()}
    _run(client, o1)
    after_plain = {c: r["stock_qty"] for c, r in _inv(client).items()}
    after_scoped = {c: r["stock_qty"] for c, r in _inv(client, o1).items()}
    assert before == after_plain == after_scoped, "生成备料单不得改动库存结存"


def test_regenerate_replaces_occupancy_not_doubles(client):
    o1, _ = _two_orders(client)
    _run(client, o1)
    first = _inv(client, o1)["I-PR"]["occupied_qty"]
    assert first == 10.0  # 40 份 × 0.25

    line = _find_line(_tree(client, o1), "D-HS", "五花肉")
    r = client.put(f"/api/bom/{line['line_id']}", params={"order_id": o1},
                   json={"qty_per_portion": 0.5})
    assert r.status_code == 200
    _run(client, o1)
    assert _inv(client, o1)["I-PR"]["occupied_qty"] == 20.0, "重新生成后占用应顶替而非累加"

    runs = client.get("/api/prep/runs", params={"order_id": o1}).json()
    assert [r["status"] for r in runs] == ["active", "voided"]


# ---------- 定额树:停在当前订单域 ----------

def test_quota_edit_isolated_between_orders(client):
    o1, o2 = _two_orders(client)
    line1 = _find_line(_tree(client, o1), "D-HS", "五花肉")
    original = line1["qty"]
    r = client.put(f"/api/bom/{line1['line_id']}", params={"order_id": o1},
                   json={"qty_per_portion": original + 0.1})
    assert r.status_code == 200
    assert _find_line(_tree(client, o1), "D-HS", "五花肉")["qty"] == original + 0.1
    assert _find_line(_tree(client, o2), "D-HS", "五花肉")["qty"] == original, "对岸定额禁止被改"


def test_cross_order_quota_write_rejected(client):
    o1, o2 = _two_orders(client)
    line2 = _find_line(_tree(client, o2), "D-YC", "茄子")
    r = client.put(f"/api/bom/{line2['line_id']}", params={"order_id": o1},
                   json={"qty_per_portion": 9.9})
    assert r.status_code == 404, "拿别单的定额行写本单,必须失败"
    assert _find_line(_tree(client, o2), "D-YC", "茄子")["qty"] == line2["qty"]


# ---------- 删除出品:未作废备料单守卫 + 原子回退 ----------

def test_delete_dish_blocked_by_active_run_and_rolls_back(client):
    o1, _ = _two_orders(client)
    dishes = {d["code"]: d for d in client.get("/api/dishes").json()}
    dhs = dishes["D-HS"]["id"]
    _run(client, o1)

    r = client.delete(f"/api/dishes/{dhs}")
    assert r.status_code == 409, "被未作废备料单用到的出品,删除必须失败"

    # 单和树都退回:出品还在、订单行还在、定额树还在
    assert any(d["id"] == dhs for d in client.get("/api/dishes").json())
    lines = client.get(f"/api/orders/{o1}/lines").json()
    assert any(l["dish_id"] == dhs for l in lines)
    assert any(d["dish_id"] == dhs for d in _tree(client, o1))

    # 作废本单备料单后(别单没有生效备料单),删除放行
    run_id = _latest(client, o1)["id"]
    assert client.post(f"/api/prep/runs/{run_id}/void", params={"order_id": o1}).status_code == 200
    assert client.delete(f"/api/dishes/{dhs}").status_code == 200
    assert not any(d["id"] == dhs for d in client.get("/api/dishes").json())
    assert not any(l["dish_id"] == dhs for l in client.get(f"/api/orders/{o1}/lines").json())
    assert not any(d["dish_id"] == dhs for d in _tree(client, o1))


def test_delete_dish_blocked_by_other_orders_run(client):
    """别单的未作废备料单同样拦住删除——守卫跨单,写仍各归各单。"""
    o1, o2 = _two_orders(client)
    _run(client, o2)
    dishes = {d["code"]: d for d in client.get("/api/dishes").json()}
    assert client.delete(f"/api/dishes/{dishes['D-JT']['id']}").status_code == 409


def test_delete_unused_dish_succeeds(client):
    client.get("/api/orders")  # 无备料单时直接可删
    dishes = {d["code"]: d for d in client.get("/api/dishes").json()}
    assert client.delete(f"/api/dishes/{dishes['D-YC']['id']}").status_code == 200


# ---------- 读入口不写,写入口必须带单 ----------

def test_reads_never_generate(client):
    _, o2 = _two_orders(client)
    assert _latest(client, o2)["prep_lines"] == []
    assert _shortages(client, o2)["shortages"] == []
    runs = client.get("/api/prep/runs", params={"order_id": o2}).json()
    assert runs == [], "读接口不得顺手生成备料单"


def test_write_and_scoped_read_require_order_id(client):
    assert client.post("/api/prep/run").status_code == 422
    assert client.put("/api/bom/1", json={"qty_per_portion": 1}).status_code == 422
    assert client.get("/api/prep/latest").status_code == 422
    assert client.get("/api/prep/shortages").status_code == 422
    assert client.get("/api/bom/tree").status_code == 422


def test_void_cross_order_rejected(client):
    o1, o2 = _two_orders(client)
    run_id = _run(client, o1)["id"]
    r = client.post(f"/api/prep/runs/{run_id}/void", params={"order_id": o2})
    assert r.status_code == 404, "作废别单备料单必须失败"
    assert _latest(client, o1)["status"] == "active"


# ---------- 全流程:本单操作,对岸全景不动 ----------

def test_full_flow_leaves_other_order_untouched(client):
    o1, o2 = _two_orders(client)
    before = {
        "tree": _tree(client, o2),
        "latest": _latest(client, o2),
        "shortages": _shortages(client, o2),
        "inv": _inv(client, o2),
    }
    # 在订单 1 上:改定额 → 生成 → 看缺料
    line = _find_line(_tree(client, o1), "D-HS", "五花肉")
    client.put(f"/api/bom/{line['line_id']}", params={"order_id": o1},
               json={"qty_per_portion": 0.4})
    _run(client, o1)
    assert _shortages(client, o1)["shortages"], "本单应有缺料"

    assert _tree(client, o2) == before["tree"]
    assert _latest(client, o2) == before["latest"]
    assert _shortages(client, o2) == before["shortages"]
    assert _inv(client, o2) == before["inv"]
