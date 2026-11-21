from collections.abc import Callable, Generator
from datetime import UTC, datetime

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from hacker_news_pipeline.config import Settings
from hacker_news_pipeline.db.orm_models import RawFeedResponse, RawItemResponse
from hacker_news_pipeline.db.session import create_database_engine


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    settings = Settings()
    database_url = settings.test_database_url

    if database_url is None:
        pytest.fail("HN_PIPELINE_TEST_DATABASE_URL environment variable is required")

    test_engine = create_database_engine(
        database_url,
    )

    if test_engine.url.database != "hacker_news_test":
        pytest.fail("Integration tests must use the hacker_news_test database")

    yield test_engine

    test_engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def raw_item_response_factory(
    db_session: Session,
) -> Callable[..., RawItemResponse]:
    def create(**overrides: object) -> RawItemResponse:
        values: dict[str, object] = {
            "source_name": "hacker_news",
            "item_id": 12,
            "response_payload": {
                "id": 12,
                "type": "story",
                "title": "A test story",
            },
            "payload_hash": "a" * 64,
            "fetched_at": datetime(2026, 1, 15, tzinfo=UTC),
        }

        values.update(overrides)

        raw_item_response = RawItemResponse(**values)

        db_session.add(raw_item_response)
        db_session.flush()

        assert raw_item_response.raw_item_response_id is not None

        return raw_item_response

    return create


@pytest.fixture
def raw_feed_response_factory(
    db_session: Session,
) -> Callable[..., RawFeedResponse]:
    def create(**overrides: object) -> RawFeedResponse:
        values: dict[str, object] = {
            "source_name": "hacker_news",
            "feed_name": "newstories",
            "response_payload": [1, 2, 3],
            "payload_hash": "a" * 64,
            "fetched_at": datetime(2026, 1, 15, tzinfo=UTC),
        }

        values.update(overrides)

        raw_feed_response = RawFeedResponse(**values)

        db_session.add(raw_feed_response)
        db_session.flush()

        assert raw_feed_response.raw_feed_response_id is not None

        return raw_feed_response

    return create
