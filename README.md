# KitPrep 中央厨房 BOM 备料

按菜品 BOM 展开订单行、合并同原料需求，对照库存计算缺料并生成备料单。

技术栈：Python 3.12 / FastAPI / SQLAlchemy / PostgreSQL / Vue 3 / TypeScript / Vite

## 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:5000 |
| API | http://localhost:10100 |
| API 文档 | http://localhost:10100/docs |
| Postgres | localhost:5451 |

健康检查：`GET http://localhost:10100/api/health`

## 使用说明

1. 顶栏订单芯片选择**当前订单**（选择保存在本地，切页不丢）。订单页、备料单、缺料贴、定额树、库存占用列都停在当前订单域。
2. 在「菜品」「BOM」维护中央厨房出品与基准用料树；在 BOM 树/备料台左树可按当前订单改「本单定额」（只覆盖本单，不动基准与别单，可一键恢复基准）。
3. 在「订单」「库存」确认当日需求与现有库存；库存结存永远不被备料单扣减。
4. 「备料单」点生成只锁当前订单（本单旧未作废单据自动作废，跨单只读不受影响）；单据可作废。
5. 在「缺料」只看当前订单未作废备料单的 need − stock 正数。
6. 出品被任一未作废备料单用到时禁止删除（接口整体回退），先作废相关备料单再删。

不使用领料出库等方式隔离订单；隔离完全由 `order_id` 订单域 + 备料单快照保证。

## 开发与测试

```bash
docker compose exec api pytest -q
```
