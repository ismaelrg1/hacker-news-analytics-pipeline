from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hacker_news_pipeline.db.orm_models import RawFeedResponse

pytestmark = pytest.mark.integration


def test_raw_feed_response_persists_and_can_be_retrieved(db_session: Session) -> None:

    response_payload = [1, 2, 3]

    fetched_at = datetime(2026, 1, 15, tzinfo=UTC)

    raw_feed_response = RawFeedResponse(
        source_name="hacker_news",
        feed_name="newstories",
        response_payload=response_payload,
        payload_hash="a" * 64,
        fetched_at=fetched_at,
    )

    db_session.add(raw_feed_response)
    db_session.flush()

    assert raw_feed_response.raw_feed_response_id is not None

    raw_feed_response_id = raw_feed_response.raw_feed_response_id

    db_session.expire_all()

    result = db_session.get(
        RawFeedResponse,
        raw_feed_response_id,
    )

    assert result is not None
    assert result.raw_feed_response_id == raw_feed_response_id
    assert result.source_name == "hacker_news"
    assert result.feed_name == "newstories"
    assert result.payload_hash == "a" * 64
    assert result.fetched_at is not None
    assert result.fetched_at == fetched_at
    assert result.response_payload == response_payload


@pytest.mark.parametrize(
    "invalid_payload_hash",
    [
        "abc",
        "g" * 64,
        "A" * 64,
        "a" * 63,
    ],
)
def test_raw_feed_response_rejects_invalid_payload_hash(
    db_session: Session,
    invalid_payload_hash: str,
) -> None:
    response_payload = [1, 2, 3]

    fetched_at = datetime(2026, 1, 15, tzinfo=UTC)

    raw_feed_response = RawFeedResponse(
        source_name="hacker_news",
        feed_name="newstories",
        response_payload=response_payload,
        payload_hash=invalid_payload_hash,
        fetched_at=fetched_at,
    )

    db_session.add(raw_feed_response)

    with pytest.raises(
        IntegrityError,
        match="chk_hn_feed_responses_payload_hash_format",
    ):
        db_session.flush()

    db_session.rollback()


def test_raw_feed_response_allows_repeated_observations(
    db_session: Session,
) -> None:

    response_payload = [1, 2, 3]

    first_fetched_at = datetime(2026, 1, 15, tzinfo=UTC)

    raw_feed_response_1 = RawFeedResponse(
        source_name="hacker_news",
        feed_name="newstories",
        response_payload=response_payload,
        payload_hash="a" * 64,
        fetched_at=first_fetched_at,
    )

    second_fetched_at = datetime(2026, 2, 15, tzinfo=UTC)

    raw_feed_response_2 = RawFeedResponse(
        source_name="hacker_news",
        feed_name="newstories",
        response_payload=response_payload,
        payload_hash="a" * 64,
        fetched_at=second_fetched_at,
    )

    db_session.add_all([raw_feed_response_1, raw_feed_response_2])
    db_session.flush()

    assert raw_feed_response_1.raw_feed_response_id is not None
    assert raw_feed_response_2.raw_feed_response_id is not None
    assert (
        raw_feed_response_1.raw_feed_response_id
        != raw_feed_response_2.raw_feed_response_id
    )

    db_session.expire_all()

    stmt = (
        select(RawFeedResponse)
        .where(
            RawFeedResponse.feed_name == "newstories",
            RawFeedResponse.payload_hash == "a" * 64,
        )
        .order_by(RawFeedResponse.fetched_at)
    )

    persisted_responses = db_session.scalars(stmt).all()

    assert len(persisted_responses) == 2
    assert (
        persisted_responses[0].raw_feed_response_id
        != persisted_responses[1].raw_feed_response_id
    )
    assert (
        persisted_responses[0].response_payload
        == persisted_responses[1].response_payload
    )
    assert persisted_responses[0].response_payload == response_payload
    assert persisted_responses[1].response_payload == response_payload
    assert persisted_responses[0].payload_hash == persisted_responses[1].payload_hash
    assert persisted_responses[0].fetched_at == first_fetched_at
    assert persisted_responses[1].fetched_at == second_fetched_at


@pytest.mark.parametrize(
    "invalid_feed_name",
    [
        "jobstories",
        "unknown",
        "",
    ],
)
def test_raw_feed_response_rejects_invalid_feed_name(
    db_session: Session,
    invalid_feed_name: str,
) -> None:
    response_payload = [1, 2, 3]

    fetched_at = datetime(2026, 1, 15, tzinfo=UTC)

    raw_feed_response = RawFeedResponse(
        source_name="hacker_news",
        feed_name=invalid_feed_name,
        response_payload=response_payload,
        payload_hash="a" * 64,
        fetched_at=fetched_at,
    )

    db_session.add(raw_feed_response)

    with pytest.raises(
        IntegrityError,
        match="chk_hn_feed_responses_supported_feed_name",
    ):
        db_session.flush()

    db_session.rollback()
