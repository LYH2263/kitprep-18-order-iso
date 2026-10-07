import os
import tempfile

# 必须在导入 app 之前指向独立测试库(临时 sqlite 文件)
_TMPDIR = tempfile.mkdtemp(prefix="kitprep_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test.db"
os.environ["SEED_ON_EMPTY"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.services.seed import seed_if_empty


@pytest.fixture()
def client():
    # 每个用例一张干净的库:重建表 + 重新播种(两张订单)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    return TestClient(app)
