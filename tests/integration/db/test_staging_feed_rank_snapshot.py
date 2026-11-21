from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hacker_news_pipeline.db.orm_models import (
    RawFeedResponse,
    StagingFeedRankSnapshot,
)

pytestmark = pytest.mark.integration


def test_staging_feed_rank_snapshot_persists_and_links_to_raw_feed_response(
    db_session: Session,
    raw_feed_response_factory: Callable[..., RawFeedResponse],
) -> None:

    raw_feed_response: RawFeedResponse = raw_feed_response_factory()

    observed_at: datetime = raw_feed_response.fetched_at

    staging_feed_rank_snapshot: StagingFeedRankSnapshot = StagingFeedRankSnapshot(
        raw_feed_response_id=raw_feed_response.raw_feed_response_id,
        feed_name="newstories",
        item_id=1,
        rank_position=1,
        observed_at=observed_at,
    )

    db_session.add(staging_feed_rank_snapshot)
    db_session.flush()

    assert staging_feed_rank_snapshot.hn_feed_rank_snapshot_id is not None
    staging_feed_rank_snapshot_id = staging_feed_rank_snapshot.hn_feed_rank_snapshot_id

    raw_feed_response_id = raw_feed_response.raw_feed_response_id

    db_session.expire_all()

    result_snapshot = db_session.get(
        StagingFeedRankSnapshot,
        staging_feed_rank_snapshot_id,
    )

    result_raw = db_session.get(
        RawFeedResponse,
        raw_feed_response_id,
    )

    assert result_snapshot is not None
    assert result_raw is not None

    assert result_snapshot.raw_feed_response_id == raw_feed_response_id
    assert (
        result_snapshot.raw_feed_response.raw_feed_response_id == raw_feed_response_id
    )

    assert len(result_raw.feed_rank_snapshots) == 1
    assert (
        result_raw.feed_rank_snapshots[0].hn_feed_rank_snapshot_id
        == staging_feed_rank_snapshot_id
    )

    assert result_snapshot.feed_name == "newstories"
    assert result_snapshot.item_id == 1
    assert result_snapshot.rank_position == 1
    assert result_snapshot.observed_at == raw_feed_response.fetched_at


@pytest.mark.parametrize("invalid_rank_position", [0, -1])
def test_staging_feed_rank_snapshot_rejects_non_positive_rank_position(
    db_session: Session,
    raw_feed_response_factory: Callable[..., RawFeedResponse],
    invalid_rank_position: int,
) -> None:
    raw_feed_response: RawFeedResponse = raw_feed_response_factory()

    observed_at: datetime = raw_feed_response.fetched_at

    staging_feed_rank_snapshot: StagingFeedRankSnapshot = StagingFeedRankSnapshot(
        raw_feed_response_id=raw_feed_response.raw_feed_response_id,
        feed_name="newstories",
        item_id=1,
        rank_position=invalid_rank_position,
        observed_at=observed_at,
    )

    with pytest.raises(
        IntegrityError,
        match="chk_feed_rank_snapshots_positive_rank_position",
    ):
        db_session.add(staging_feed_rank_snapshot)
        db_session.flush()

    db_session.rollback()


@pytest.mark.parametrize("invalid_feed_name", ["jobstories", "unknown", ""])
def test_staging_feed_rank_snapshot_rejects_unsupported_feed_name(
    db_session: Session,
    raw_feed_response_factory: Callable[..., RawFeedResponse],
    invalid_feed_name: str,
) -> None:
    raw_feed_response: RawFeedResponse = raw_feed_response_factory()

    observed_at: datetime = raw_feed_response.fetched_at

    staging_feed_rank_snapshot: StagingFeedRankSnapshot = StagingFeedRankSnapshot(
        raw_feed_response_id=raw_feed_response.raw_feed_response_id,
        feed_name=invalid_feed_name,
        item_id=1,
        rank_position=1,
        observed_at=observed_at,
    )

    with pytest.raises(
        IntegrityError,
        match="chk_feed_rank_snapshots_supported_feed_name",
    ):
        db_session.add(staging_feed_rank_snapshot)
        db_session.flush()

    db_session.rollback()


def test_staging_feed_rank_snapshot_rejects_nonexistent_raw_feed_response(
    db_session: Session,
) -> None:

    observed_at: datetime = datetime(2026, 1, 15, tzinfo=UTC)

    staging_feed_rank_snapshot: StagingFeedRankSnapshot = StagingFeedRankSnapshot(
        raw_feed_response_id=999_999_999_999,
        feed_name="newstories",
        item_id=1,
        rank_position=1,
        observed_at=observed_at,
    )

    with pytest.raises(
        IntegrityError,
        match="violates foreign key constraint",
    ):
        db_session.add(staging_feed_rank_snapshot)
        db_session.flush()

    db_session.rollback()


def test_staging_feed_rank_snapshot_rejects_duplicate_rank_position_per_feed_response(
    db_session: Session,
    raw_feed_response_factory: Callable[..., RawFeedResponse],
) -> None:

    raw_feed_response: RawFeedResponse = raw_feed_response_factory()

    observed_at: datetime = raw_feed_response.fetched_at

    staging_feed_rank_snapshot_1: StagingFeedRankSnapshot = StagingFeedRankSnapshot(
        raw_feed_response_id=raw_feed_response.raw_feed_response_id,
        feed_name="newstories",
        item_id=1,
        rank_position=1,
        observed_at=observed_at,
    )

    db_session.add(staging_feed_rank_snapshot_1)
    db_session.flush()

    staging_feed_rank_snapshot_2: StagingFeedRankSnapshot = StagingFeedRankSnapshot(
        raw_feed_response_id=raw_feed_response.raw_feed_response_id,
        feed_name="newstories",
        item_id=2,
        rank_position=1,
        observed_at=observed_at,
    )

    with pytest.raises(
        IntegrityError,
        match="uq_feed_rank_snapshots_feed_response_rank_position",
    ):
        db_session.add(staging_feed_rank_snapshot_2)
        db_session.flush()

    db_session.rollback()


def test_staging_feed_rank_snapshot_rejects_duplicate_item_per_feed_response(
    db_session: Session,
    raw_feed_response_factory: Callable[..., RawFeedResponse],
) -> None:

    raw_feed_response: RawFeedResponse = raw_feed_response_factory()

    observed_at: datetime = raw_feed_response.fetched_at

    staging_feed_rank_snapshot_1: StagingFeedRankSnapshot = StagingFeedRankSnapshot(
        raw_feed_response_id=raw_feed_response.raw_feed_response_id,
        feed_name="newstories",
        item_id=1,
        rank_position=1,
        observed_at=observed_at,
    )

    db_session.add(staging_feed_rank_snapshot_1)
    db_session.flush()

    staging_feed_rank_snapshot_2: StagingFeedRankSnapshot = StagingFeedRankSnapshot(
        raw_feed_response_id=raw_feed_response.raw_feed_response_id,
        feed_name="newstories",
        item_id=1,
        rank_position=2,
        observed_at=observed_at,
    )

    with pytest.raises(
        IntegrityError,
        match="uq_feed_rank_snapshots_feed_response_item_id",
    ):
        db_session.add(staging_feed_rank_snapshot_2)
        db_session.flush()

    db_session.rollback()


def test_staging_feed_rank_snapshot_allows_same_item_in_different_feed_responses(
    db_session: Session,
    raw_feed_response_factory: Callable[..., RawFeedResponse],
) -> None:

    raw_feed_response_1: RawFeedResponse = raw_feed_response_factory()

    raw_feed_response_2: RawFeedResponse = raw_feed_response_factory()

    observed_at_1: datetime = raw_feed_response_1.fetched_at
    observed_at_2: datetime = raw_feed_response_2.fetched_at

    staging_feed_rank_snapshot_1: StagingFeedRankSnapshot = StagingFeedRankSnapshot(
        raw_feed_response_id=raw_feed_response_1.raw_feed_response_id,
        feed_name="newstories",
        item_id=1,
        rank_position=1,
        observed_at=observed_at_1,
    )

    staging_feed_rank_snapshot_2: StagingFeedRankSnapshot = StagingFeedRankSnapshot(
        raw_feed_response_id=raw_feed_response_2.raw_feed_response_id,
        feed_name="newstories",
        item_id=1,
        rank_position=1,
        observed_at=observed_at_2,
    )

    db_session.add_all([staging_feed_rank_snapshot_1, staging_feed_rank_snapshot_2])
    db_session.flush()

    assert staging_feed_rank_snapshot_1.hn_feed_rank_snapshot_id is not None
    staging_feed_rank_snapshot_id_1 = (
        staging_feed_rank_snapshot_1.hn_feed_rank_snapshot_id
    )

    assert staging_feed_rank_snapshot_2.hn_feed_rank_snapshot_id is not None
    staging_feed_rank_snapshot_id_2 = (
        staging_feed_rank_snapshot_2.hn_feed_rank_snapshot_id
    )

    raw_feed_response_id_1 = raw_feed_response_1.raw_feed_response_id
    raw_feed_response_id_2 = raw_feed_response_2.raw_feed_response_id

    assert raw_feed_response_id_1 != raw_feed_response_id_2

    db_session.expire_all()

    result_snapshot_1 = db_session.get(
        StagingFeedRankSnapshot,
        staging_feed_rank_snapshot_id_1,
    )
    result_snapshot_2 = db_session.get(
        StagingFeedRankSnapshot,
        staging_feed_rank_snapshot_id_2,
    )

    assert result_snapshot_1 is not None
    assert result_snapshot_2 is not None

    assert (
        result_snapshot_1.hn_feed_rank_snapshot_id
        != result_snapshot_2.hn_feed_rank_snapshot_id
    )

    assert result_snapshot_1.item_id == 1
    assert result_snapshot_2.item_id == 1

    assert result_snapshot_1.rank_position == 1
    assert result_snapshot_2.rank_position == 1
