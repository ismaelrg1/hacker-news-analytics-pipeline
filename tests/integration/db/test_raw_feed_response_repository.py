from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from hacker_news_pipeline.db.orm_models import RawFeedResponse
from hacker_news_pipeline.db.raw_repositories import RawFeedResponseRepository

pytestmark = pytest.mark.integration


def test_create_feed_response_persists_and_returns_raw_response(
    db_session: Session,
) -> None:
    repository = RawFeedResponseRepository(db_session)

    response_payload = [1, 2, 3]

    payload_hash = "a" * 64

    fetched_at = datetime(2026, 1, 15, tzinfo=UTC)

    feed_response = repository.create_feed_response(
        source_name="hacker_news",
        feed_name="newstories",
        response_payload=response_payload,
        payload_hash=payload_hash,
        fetched_at=fetched_at,
    )

    # 1. Verify the returned object.
    assert feed_response.raw_feed_response_id is not None
    assert feed_response.fetched_at is not None

    assert feed_response.source_name == "hacker_news"
    assert feed_response.feed_name == "newstories"
    assert feed_response.response_payload == response_payload
    assert feed_response.payload_hash == payload_hash

    raw_feed_response_id = feed_response.raw_feed_response_id

    # 2. Expire the session cache.
    db_session.expire_all()

    # 3. Retrieve the record from PostgreSQL.
    persisted_feed_response = db_session.get(
        RawFeedResponse,
        raw_feed_response_id,
    )

    # 4. Verify that the record actually exists.
    assert persisted_feed_response is not None
    assert persisted_feed_response.raw_feed_response_id == raw_feed_response_id
    assert persisted_feed_response.source_name == "hacker_news"
    assert persisted_feed_response.feed_name == "newstories"
    assert persisted_feed_response.payload_hash == payload_hash
    assert persisted_feed_response.fetched_at is not None
    assert persisted_feed_response.fetched_at == fetched_at
    assert persisted_feed_response.response_payload == response_payload
