"""测试固定装置"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

TEST_DB_URL = "sqlite:///./test.db"


@pytest.fixture
def db_session():
    engine = create_engine(TEST_DB_URL, echo=False)
    from db import DBModelBase
    DBModelBase.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    DBModelBase.metadata.drop_all(engine)


@pytest.fixture
def test_app():
    from app.main import create_app
    return create_app()


@pytest_asyncio.fixture
async def async_client(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        yield client
