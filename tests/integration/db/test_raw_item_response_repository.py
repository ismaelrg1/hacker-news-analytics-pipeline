from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from hacker_news_pipeline.db.orm_models import RawItemResponse
from hacker_news_pipeline.db.raw_repositories import RawItemResponseRepository

pytestmark = pytest.mark.integration


def test_create_item_response_persists_and_returns_raw_response(
    db_session: Session,
) -> None:
    repository = RawItemResponseRepository(db_session)

    response_payload = {
        "id": 12,
        "type": "story",
        "title": "A test story",
    }

    payload_hash = "a" * 64

    fetched_at = datetime(2026, 1, 15, tzinfo=UTC)

    item_response = repository.create_item_response(
        source_name="hacker_news",
        item_id=12,
        response_payload=response_payload,
        payload_hash=payload_hash,
        fetched_at=fetched_at,
    )

    # 1. Verify the returned object.
    assert item_response.raw_item_response_id is not None
    assert item_response.fetched_at is not None

    assert item_response.source_name == "hacker_news"
    assert item_response.item_id == 12
    assert item_response.response_payload == response_payload
    assert item_response.payload_hash == payload_hash

    raw_item_response_id = item_response.raw_item_response_id

    # 2. Expire the session cache.
    db_session.expire_all()

    # 3. Retrieve the record from PostgreSQL.
    persisted_item_response = db_session.get(
        RawItemResponse,
        raw_item_response_id,
    )

    # 4. Verify that the record actually exists.
    assert persisted_item_response is not None
    assert persisted_item_response.raw_item_response_id == raw_item_response_id
    assert persisted_item_response.source_name == "hacker_news"
    assert persisted_item_response.item_id == 12
    assert persisted_item_response.payload_hash == payload_hash
    assert persisted_item_response.fetched_at is not None
    assert persisted_item_response.fetched_at == fetched_at
    assert persisted_item_response.response_payload == response_payload
