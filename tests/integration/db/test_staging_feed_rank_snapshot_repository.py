from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from hacker_news_pipeline.db.orm_models import (
    RawFeedResponse,
    StagingFeedRankSnapshot,
)
from hacker_news_pipeline.db.staging_repositories import (
    StagingFeedRankSnapshotRepository,
)

pytestmark = pytest.mark.integration


def test_insert_rank_snapshots_if_absent_persists_feed_positions(
    db_session: Session, raw_feed_response_factory: Callable[..., RawFeedResponse]
) -> None:
    observed_at = datetime(2026, 1, 15, tzinfo=UTC)

    raw_feed_response: RawFeedResponse = raw_feed_response_factory(
        feed_name="topstories",
        response_payload=[101, 202, 303],
        fetched_at=observed_at,
    )

    repository = StagingFeedRankSnapshotRepository(
        session=db_session,
    )

    inserted_count = repository.insert_rank_snapshots_if_absent(
        raw_feed_response=raw_feed_response,
    )

    assert inserted_count == 3

    raw_feed_response_id = raw_feed_response.raw_feed_response_id

    db_session.expire_all()

    stmt = (
        select(StagingFeedRankSnapshot)
        .where(StagingFeedRankSnapshot.raw_feed_response_id == raw_feed_response_id)
        .order_by(StagingFeedRankSnapshot.rank_position)
    )

    persisted_snapshots = db_session.scalars(stmt).all()

    assert len(persisted_snapshots) == 3

    first_snapshot, second_snapshot, third_snapshot = persisted_snapshots

    assert first_snapshot.item_id == 101
    assert first_snapshot.rank_position == 1

    assert second_snapshot.item_id == 202
    assert second_snapshot.rank_position == 2

    assert third_snapshot.item_id == 303
    assert third_snapshot.rank_position == 3

    for snapshot in persisted_snapshots:
        assert snapshot.raw_feed_response_id == raw_feed_response_id
        assert snapshot.feed_name == "topstories"
        assert snapshot.observed_at == observed_at


def test_insert_rank_snapshots_if_absent_ignores_existing_snapshots(
    db_session: Session, raw_feed_response_factory: Callable[..., RawFeedResponse]
) -> None:
    observed_at = datetime(2026, 1, 15, tzinfo=UTC)

    raw_feed_response: RawFeedResponse = raw_feed_response_factory(
        feed_name="topstories",
        response_payload=[101, 202, 303],
        fetched_at=observed_at,
    )

    repository = StagingFeedRankSnapshotRepository(
        session=db_session,
    )

    inserted_count_1 = repository.insert_rank_snapshots_if_absent(
        raw_feed_response=raw_feed_response,
    )

    inserted_count_2 = repository.insert_rank_snapshots_if_absent(
        raw_feed_response=raw_feed_response,
    )

    assert inserted_count_1 == 3
    assert inserted_count_2 == 0

    raw_feed_response_id = raw_feed_response.raw_feed_response_id

    db_session.expire_all()

    stmt = (
        select(StagingFeedRankSnapshot)
        .where(StagingFeedRankSnapshot.raw_feed_response_id == raw_feed_response_id)
        .order_by(StagingFeedRankSnapshot.rank_position)
    )

    persisted_snapshots = db_session.scalars(stmt).all()

    assert len(persisted_snapshots) == 3


def test_insert_rank_snapshots_if_absent_allows_same_items_for_different_raw_feed_responses(
    db_session: Session, raw_feed_response_factory: Callable[..., RawFeedResponse]
) -> None:
    observed_at_1 = datetime(2026, 1, 15, tzinfo=UTC)
    observed_at_2 = datetime(2026, 1, 16, tzinfo=UTC)

    raw_feed_response_1: RawFeedResponse = raw_feed_response_factory(
        feed_name="topstories",
        response_payload=[101, 202, 303],
        fetched_at=observed_at_1,
    )

    raw_feed_response_2: RawFeedResponse = raw_feed_response_factory(
        feed_name="topstories",
        response_payload=[101, 202, 303],
        fetched_at=observed_at_2,
    )

    repository = StagingFeedRankSnapshotRepository(
        session=db_session,
    )

    inserted_count_1 = repository.insert_rank_snapshots_if_absent(
        raw_feed_response=raw_feed_response_1,
    )

    inserted_count_2 = repository.insert_rank_snapshots_if_absent(
        raw_feed_response=raw_feed_response_2,
    )

    assert inserted_count_1 == 3
    assert inserted_count_2 == 3

    raw_feed_response_id_1 = raw_feed_response_1.raw_feed_response_id
    raw_feed_response_id_2 = raw_feed_response_2.raw_feed_response_id

    assert raw_feed_response_id_1 != raw_feed_response_id_2

    db_session.expire_all()

    stmt = (
        select(StagingFeedRankSnapshot)
        .where(
            StagingFeedRankSnapshot.raw_feed_response_id.in_(
                [
                    raw_feed_response_id_1,
                    raw_feed_response_id_2,
                ]
            )
        )
        .order_by(
            StagingFeedRankSnapshot.raw_feed_response_id,
            StagingFeedRankSnapshot.rank_position,
        )
    )

    persisted_snapshots = db_session.scalars(stmt).all()

    assert len(persisted_snapshots) == 6

    first_snapshots = [
        snapshot
        for snapshot in persisted_snapshots
        if snapshot.raw_feed_response_id == raw_feed_response_id_1
    ]

    second_snapshots = [
        snapshot
        for snapshot in persisted_snapshots
        if snapshot.raw_feed_response_id == raw_feed_response_id_2
    ]

    assert len(first_snapshots) == 3
    assert len(second_snapshots) == 3

    assert [snapshot.rank_position for snapshot in first_snapshots] == [1, 2, 3]
    assert [snapshot.rank_position for snapshot in second_snapshots] == [1, 2, 3]

    assert {snapshot.observed_at for snapshot in first_snapshots} == {observed_at_1}
    assert {snapshot.observed_at for snapshot in second_snapshots} == {observed_at_2}


def test_insert_rank_snapshots_if_absent_returns_zero_for_empty_feed(
    db_session: Session, raw_feed_response_factory: Callable[..., RawFeedResponse]
) -> None:

    raw_feed_response: RawFeedResponse = raw_feed_response_factory(
        feed_name="topstories", response_payload=[]
    )

    repository = StagingFeedRankSnapshotRepository(
        session=db_session,
    )

    inserted_count = repository.insert_rank_snapshots_if_absent(
        raw_feed_response=raw_feed_response,
    )

    assert inserted_count == 0

    raw_feed_response_id = raw_feed_response.raw_feed_response_id

    assert raw_feed_response_id is not None

    db_session.expire_all()

    stmt = select(StagingFeedRankSnapshot).where(
        StagingFeedRankSnapshot.raw_feed_response_id == raw_feed_response_id
    )

    persisted_snapshots = db_session.scalars(stmt).all()

    assert len(persisted_snapshots) == 0
