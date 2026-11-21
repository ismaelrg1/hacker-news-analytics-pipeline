from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hacker_news_pipeline.db.orm_models import (
    RawItemResponse,
    StagingItemVersion,
)

pytestmark = pytest.mark.integration


def test_staging_item_version_persists_and_links_to_raw_item_response(
    db_session: Session,
    raw_item_response_factory: Callable[..., RawItemResponse],
) -> None:

    raw_item_response: RawItemResponse = raw_item_response_factory()

    staging_item_version: StagingItemVersion = StagingItemVersion(
        item_id=12,
        payload_hash="a" * 64,
        first_raw_response_id=raw_item_response.raw_item_response_id,
        first_seen_at=datetime(2026, 1, 15, tzinfo=UTC),
        last_seen_at=datetime(2026, 1, 15, tzinfo=UTC),
        item_type="story",
    )

    db_session.add(staging_item_version)
    db_session.flush()

    assert staging_item_version.hn_item_version_id is not None
    staging_item_version_id = staging_item_version.hn_item_version_id

    raw_item_response_id = raw_item_response.raw_item_response_id

    db_session.expire_all()

    result_version = db_session.get(
        StagingItemVersion,
        staging_item_version_id,
    )

    result_raw = db_session.get(RawItemResponse, raw_item_response_id)

    assert result_version is not None
    assert result_raw is not None

    assert result_version.first_raw_response_id == raw_item_response_id
    assert (
        result_version.first_raw_response.raw_item_response_id == raw_item_response_id
    )

    assert result_raw.item_version is not None
    assert result_raw.item_version.hn_item_version_id == staging_item_version_id

    assert result_version.is_deleted is False
    assert result_version.is_dead is False


def test_staging_item_version_rejects_duplicate_item_id_and_payload_hash(
    db_session: Session,
    raw_item_response_factory: Callable[..., RawItemResponse],
) -> None:
    raw_item_response_1: RawItemResponse = raw_item_response_factory()
    raw_item_response_2: RawItemResponse = raw_item_response_factory()

    staging_item_version_1: StagingItemVersion = StagingItemVersion(
        item_id=12,
        payload_hash="a" * 64,
        first_raw_response_id=raw_item_response_1.raw_item_response_id,
        first_seen_at=datetime(2026, 1, 15, tzinfo=UTC),
        last_seen_at=datetime(2026, 1, 15, tzinfo=UTC),
        item_type="story",
    )

    assert raw_item_response_1.raw_item_response_id is not None
    assert raw_item_response_2.raw_item_response_id is not None
    assert (
        raw_item_response_1.raw_item_response_id
        != raw_item_response_2.raw_item_response_id
    )

    db_session.add(staging_item_version_1)
    db_session.flush()

    staging_item_version_2: StagingItemVersion = StagingItemVersion(
        item_id=12,
        payload_hash="a" * 64,
        first_raw_response_id=raw_item_response_2.raw_item_response_id,
        first_seen_at=datetime(2026, 1, 15, tzinfo=UTC),
        last_seen_at=datetime(2026, 1, 15, tzinfo=UTC),
        item_type="story",
    )

    with pytest.raises(
        IntegrityError,
        match="uq_item_version_item_id_payload",
    ):
        db_session.add(staging_item_version_2)
        db_session.flush()

    db_session.rollback()


def test_staging_item_version_rejects_reused_first_raw_response(
    db_session: Session,
    raw_item_response_factory: Callable[..., RawItemResponse],
) -> None:
    raw_item_response: RawItemResponse = raw_item_response_factory()

    staging_item_version_1: StagingItemVersion = StagingItemVersion(
        item_id=12,
        payload_hash="a" * 64,
        first_raw_response_id=raw_item_response.raw_item_response_id,
        first_seen_at=datetime(2026, 1, 15, tzinfo=UTC),
        last_seen_at=datetime(2026, 1, 15, tzinfo=UTC),
        item_type="story",
    )

    db_session.add(staging_item_version_1)
    db_session.flush()

    staging_item_version_2: StagingItemVersion = StagingItemVersion(
        item_id=12,
        payload_hash="b" * 64,
        first_raw_response_id=raw_item_response.raw_item_response_id,
        first_seen_at=datetime(2026, 1, 15, tzinfo=UTC),
        last_seen_at=datetime(2026, 1, 15, tzinfo=UTC),
        item_type="story",
    )

    with pytest.raises(
        IntegrityError,
        match="uq_item_versions_first_raw_response_id",
    ):
        db_session.add(staging_item_version_2)
        db_session.flush()

    db_session.rollback()


def test_staging_item_version_rejects_nonexistent_raw_item_response(
    db_session: Session,
) -> None:
    staging_item_version: StagingItemVersion = StagingItemVersion(
        item_id=12,
        payload_hash="a" * 64,
        first_raw_response_id=999_999_999_999,
        first_seen_at=datetime(2026, 1, 15, tzinfo=UTC),
        last_seen_at=datetime(2026, 1, 15, tzinfo=UTC),
        item_type="story",
    )

    with pytest.raises(
        IntegrityError,
        match="violates foreign key constraint",
    ):
        db_session.add(staging_item_version)
        db_session.flush()

    db_session.rollback()


def test_staging_item_version_rejects_last_seen_at_before_first_seen_at(
    db_session: Session,
    raw_item_response_factory: Callable[..., RawItemResponse],
) -> None:
    raw_item_response: RawItemResponse = raw_item_response_factory()

    staging_item_version: StagingItemVersion = StagingItemVersion(
        item_id=12,
        payload_hash="a" * 64,
        first_raw_response_id=raw_item_response.raw_item_response_id,
        first_seen_at=datetime(2026, 2, 15, tzinfo=UTC),
        last_seen_at=datetime(2026, 1, 15, tzinfo=UTC),
        item_type="story",
    )

    with pytest.raises(
        IntegrityError,
        match="chk_item_versions_last_seen_at_after_first_seen_at",
    ):
        db_session.add(staging_item_version)
        db_session.flush()

    db_session.rollback()


@pytest.mark.parametrize(
    ("overrides", "constraint_name"),
    [
        ({"payload_hash": "invalid"}, "chk_item_versions_payload_hash_format"),
        ({"item_type": "video"}, "chk_item_versions_supported_item_type"),
        ({"score": -1}, "chk_item_versions_null_or_positive_score"),
        (
            {"descendants_count": -1},
            "chk_item_versions_null_or_positive_descendants_count",
        ),
    ],
)
def test_staging_item_version_rejects_invalid_domain_values(
    db_session: Session,
    raw_item_response_factory: Callable[..., RawItemResponse],
    overrides: dict[str, object],
    constraint_name: str,
) -> None:

    raw_item_response: RawItemResponse = raw_item_response_factory()

    values: dict[str, object] = {
        "item_id": 12,
        "payload_hash": "a" * 64,
        "first_raw_response_id": raw_item_response.raw_item_response_id,
        "first_seen_at": datetime(2026, 1, 15, tzinfo=UTC),
        "last_seen_at": datetime(2026, 1, 15, tzinfo=UTC),
        "item_type": "story",
    }

    values.update(overrides)

    staging_item_version: StagingItemVersion = StagingItemVersion(**values)

    with pytest.raises(
        IntegrityError,
        match=constraint_name,
    ):
        db_session.add(staging_item_version)
        db_session.flush()

    db_session.rollback()
