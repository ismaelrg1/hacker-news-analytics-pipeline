from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from hacker_news_pipeline.api.schemas import HackerNewsItemResponse
from hacker_news_pipeline.db.orm_models import RawItemResponse, StagingItemVersion
from hacker_news_pipeline.db.staging_repositories import StagingItemVersionRepository

pytestmark = pytest.mark.integration


def test_upsert_item_version_creates_a_new_staging_version(
    db_session: Session, raw_item_response_factory: Callable[..., RawItemResponse]
) -> None:

    raw_item_response: RawItemResponse = raw_item_response_factory()

    item: HackerNewsItemResponse = HackerNewsItemResponse.model_validate(
        {
            "id": raw_item_response.item_id,
            "type": "story",
            "by": "test_author",
            "time": 1768435200,
            "title": "A test story",
            "text": "Story body",
            "url": "https://example.com/story",
            "score": 42,
            "descendants": 5,
        }
    )

    assert item.created_at_unix is not None

    created_at = datetime.fromtimestamp(
        item.created_at_unix,
        tz=UTC,
    )

    repository = StagingItemVersionRepository(session=db_session)

    inserted_version = repository.upsert_item_version(
        raw_item_response=raw_item_response,
        item=item,
        created_at=created_at,
    )

    assert inserted_version.hn_item_version_id is not None
    assert inserted_version.item_id == raw_item_response.item_id
    assert inserted_version.payload_hash == raw_item_response.payload_hash
    assert (
        inserted_version.first_raw_response_id == raw_item_response.raw_item_response_id
    )
    assert inserted_version.first_seen_at == raw_item_response.fetched_at
    assert inserted_version.last_seen_at == raw_item_response.fetched_at

    assert inserted_version.item_type == "story"
    assert inserted_version.author_username == "test_author"
    assert inserted_version.created_at == created_at
    assert inserted_version.title == "A test story"
    assert inserted_version.text == "Story body"
    assert inserted_version.url == "https://example.com/story"
    assert inserted_version.score == 42
    assert inserted_version.descendants_count == 5
    assert inserted_version.is_deleted is False
    assert inserted_version.is_dead is False

    version_id = inserted_version.hn_item_version_id

    db_session.expire_all()

    persisted_version = db_session.get(
        StagingItemVersion,
        version_id,
    )

    assert persisted_version is not None
    assert persisted_version.item_id == raw_item_response.item_id
    assert persisted_version.payload_hash == raw_item_response.payload_hash

    assert persisted_version.title == "A test story"
    assert persisted_version.created_at == created_at


def test_upsert_item_version_updates_last_seen_for_existing_version(
    db_session: Session, raw_item_response_factory: Callable[..., RawItemResponse]
) -> None:
    item_id = 12
    payload_hash = "a" * 64
    first_seen_at = datetime(2026, 1, 15, tzinfo=UTC)
    second_seen_at = datetime(2026, 2, 15, tzinfo=UTC)

    raw_item_response_1 = raw_item_response_factory(
        item_id=item_id,
        payload_hash=payload_hash,
        fetched_at=first_seen_at,
    )

    raw_item_response_2 = raw_item_response_factory(
        item_id=item_id,
        payload_hash=payload_hash,
        fetched_at=second_seen_at,
    )

    item: HackerNewsItemResponse = HackerNewsItemResponse.model_validate(
        {
            "id": item_id,
            "type": "story",
            "by": "test_author",
            "time": 1768435200,
            "title": "A test story",
            "text": "Story body",
            "url": "https://example.com/story",
            "score": 42,
            "descendants": 5,
        }
    )

    assert item.created_at_unix is not None

    created_at = datetime.fromtimestamp(
        item.created_at_unix,
        tz=UTC,
    )

    repository = StagingItemVersionRepository(session=db_session)

    first_version = repository.upsert_item_version(
        raw_item_response=raw_item_response_1,
        item=item,
        created_at=created_at,
    )

    second_version = repository.upsert_item_version(
        raw_item_response=raw_item_response_2,
        item=item,
        created_at=created_at,
    )

    assert first_version.hn_item_version_id == second_version.hn_item_version_id
    assert (
        second_version.first_raw_response_id == raw_item_response_1.raw_item_response_id
    )
    assert second_version.first_seen_at == first_seen_at
    assert second_version.last_seen_at == second_seen_at

    db_session.expire_all()

    stmt = select(StagingItemVersion).where(
        StagingItemVersion.item_id == item_id,
        StagingItemVersion.payload_hash == payload_hash,
    )

    persisted_version = db_session.scalars(stmt).all()

    assert len(persisted_version) == 1

    persisted_version = persisted_version[0]

    assert (
        persisted_version.first_raw_response_id
        == raw_item_response_1.raw_item_response_id
    )
    assert persisted_version.first_seen_at == first_seen_at
    assert persisted_version.last_seen_at == second_seen_at
    assert persisted_version.title == "A test story"


def test_upsert_item_version_rejects_raw_response_for_differet_item(
    db_session: Session, raw_item_response_factory: Callable[..., RawItemResponse]
) -> None:
    item_id = 12

    raw_item_response: RawItemResponse = raw_item_response_factory(item_id=item_id)

    item: HackerNewsItemResponse = HackerNewsItemResponse.model_validate({"id": 13})

    repository = StagingItemVersionRepository(session=db_session)

    with pytest.raises(
        ValueError,
        match="same item_id",
    ):
        repository.upsert_item_version(
            raw_item_response=raw_item_response,
            item=item,
            created_at=None,
        )


def test_upsert_item_version_does_not_move_lst_seen_at_backwards(
    db_session: Session, raw_item_response_factory: Callable[..., RawItemResponse]
) -> None:
    item_id = 12
    payload_hash = "a" * 64
    latest_seen_at = datetime(2026, 2, 15, tzinfo=UTC)
    older_seen_at = datetime(2026, 1, 15, tzinfo=UTC)

    latest_raw_response = raw_item_response_factory(
        item_id=item_id,
        payload_hash=payload_hash,
        fetched_at=latest_seen_at,
    )

    older_raw_response = raw_item_response_factory(
        item_id=item_id,
        payload_hash=payload_hash,
        fetched_at=older_seen_at,
    )

    item = HackerNewsItemResponse.model_validate(
        {
            "id": item_id,
            "type": "story",
        }
    )

    repository = StagingItemVersionRepository(session=db_session)

    first_version = repository.upsert_item_version(
        raw_item_response=latest_raw_response,
        item=item,
        created_at=None,
    )

    second_version = repository.upsert_item_version(
        raw_item_response=older_raw_response,
        item=item,
        created_at=None,
    )

    assert first_version.hn_item_version_id == second_version.hn_item_version_id
    assert second_version.last_seen_at == latest_seen_at

    db_session.expire_all()

    stmt = select(StagingItemVersion).where(
        StagingItemVersion.item_id == item_id,
        StagingItemVersion.payload_hash == payload_hash,
    )

    persisted_versions = db_session.scalars(stmt).all()

    assert len(persisted_versions) == 1
    assert persisted_versions[0].last_seen_at == latest_seen_at
