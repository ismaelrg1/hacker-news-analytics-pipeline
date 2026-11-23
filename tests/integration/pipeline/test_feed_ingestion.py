from unittest.mock import Mock

import pytest
from sqlalchemy import delete, select
from sqlalchemy.engine import Engine

from hacker_news_pipeline.api.hacker_news_client import (
    HackerNewsClient,
    HackerNewsFeedFetch,
)
from hacker_news_pipeline.api.schemas import HackerNewsFeedResponse
from hacker_news_pipeline.db.orm_models import (
    RawFeedResponse,
    StagingFeedRankSnapshot,
)
from hacker_news_pipeline.db.session import create_session_factory
from hacker_news_pipeline.pipeline.feed_ingestion import ingest_feed
from hacker_news_pipeline.pipeline.hashing import calculate_payload_hash

pytestmark = pytest.mark.integration


def test_ingest_feed_persists_raw_feed_and_rank_snapshots(engine: Engine) -> None:
    # Arrange: preparar una respuesta simulada
    raw_payload = [101, 202, 303]

    client = Mock(spec=HackerNewsClient)
    client.get_feed.return_value = HackerNewsFeedFetch(
        raw_payload=raw_payload,
        feed=HackerNewsFeedResponse.model_validate(raw_payload),
    )

    session_factory = create_session_factory(engine)

    result = None
    raw_feed_response_id: int | None = None

    try:
        # Act: Ejecutar el proceso de ingestion
        result = ingest_feed(
            client=client,
            session_factory=session_factory,
            feed_name="topstories",
        )

        raw_feed_response_id = result.raw_feed_response_id

        assert result.feed_name == "topstories"
        assert result.item_ids == (101, 202, 303)
        assert result.fetched_item_count == 3
        assert result.inserted_rank_snapshot_count == 3
        assert result.raw_feed_response_id is not None

        client.get_feed.assert_called_once_with(feed_name="topstories")

        # Consultar de nuevo PostgreSQL con una sesion independiente.
        with session_factory() as session:
            raw = session.get(RawFeedResponse, raw_feed_response_id)

            assert raw is not None
            assert raw.source_name == "hacker_news"
            assert raw.feed_name == "topstories"
            assert raw.response_payload == [101, 202, 303]
            assert raw.payload_hash == calculate_payload_hash(raw_payload)
            assert raw.fetched_at is not None

            # Verificar staging
            stmt = (
                select(StagingFeedRankSnapshot)
                .where(
                    StagingFeedRankSnapshot.raw_feed_response_id == raw_feed_response_id
                )
                .order_by(StagingFeedRankSnapshot.rank_position)
            )

            staging_snapshots = session.scalars(stmt).all()

            assert len(staging_snapshots) == 3

            assert staging_snapshots[0].item_id == 101
            assert staging_snapshots[1].item_id == 202
            assert staging_snapshots[2].item_id == 303

            assert staging_snapshots[0].rank_position == 1
            assert staging_snapshots[1].rank_position == 2
            assert staging_snapshots[2].rank_position == 3

            assert staging_snapshots[0].observed_at == raw.fetched_at
            assert staging_snapshots[1].observed_at == raw.fetched_at
            assert staging_snapshots[2].observed_at == raw.fetched_at

    finally:
        # Eliminar staging records antes de eliminar el raw ingestion
        with session_factory.begin() as session:
            session.execute(
                delete(StagingFeedRankSnapshot).where(
                    StagingFeedRankSnapshot.raw_feed_response_id == raw_feed_response_id
                )
            )

            session.execute(
                delete(RawFeedResponse).where(
                    RawFeedResponse.raw_feed_response_id == raw_feed_response_id
                )
            )


def test_ingest_feed_persists_repeated_feed_observations(engine: Engine) -> None:
    # Arrange: preparar una respuesta simulada
    raw_payload = [101, 202, 303]

    client = Mock(spec=HackerNewsClient)
    client.get_feed.return_value = HackerNewsFeedFetch(
        raw_payload=raw_payload,
        feed=HackerNewsFeedResponse.model_validate(raw_payload),
    )

    session_factory = create_session_factory(engine)

    raw_feed_response_ids: list[int] = []

    try:
        # Act: Ejecutar el proceso de ingestion
        first_result = ingest_feed(
            client=client,
            session_factory=session_factory,
            feed_name="topstories",
        )

        raw_feed_response_ids.append(first_result.raw_feed_response_id)

        second_result = ingest_feed(
            client=client,
            session_factory=session_factory,
            feed_name="topstories",
        )

        raw_feed_response_ids.append(second_result.raw_feed_response_id)

        # Assert: pipeline results
        assert first_result.feed_name == "topstories"
        assert first_result.item_ids == (101, 202, 303)
        assert first_result.fetched_item_count == 3
        assert first_result.inserted_rank_snapshot_count == 3

        assert second_result.feed_name == "topstories"
        assert second_result.item_ids == (101, 202, 303)
        assert second_result.fetched_item_count == 3
        assert second_result.inserted_rank_snapshot_count == 3

        assert first_result.raw_feed_response_id != second_result.raw_feed_response_id
        assert client.get_feed.call_count == 2

        # Consultar de nuevo PostgreSQL con una sesion independiente.
        with session_factory() as session:
            stmt = select(RawFeedResponse).where(
                RawFeedResponse.raw_feed_response_id.in_(raw_feed_response_ids)
            )

            raws = session.scalars(stmt).all()

            assert len(raws) == 2

            raw_by_id = {raw.raw_feed_response_id: raw for raw in raws}

            assert set(raw_by_id) == set(raw_feed_response_ids)

            for raw in raws:
                assert raw.source_name == "hacker_news"
                assert raw.feed_name == "topstories"
                assert raw.response_payload == raw_payload
                assert raw.payload_hash == calculate_payload_hash(raw_payload)
                assert raw.fetched_at is not None

            # Verificar staging
            stmt = (
                select(StagingFeedRankSnapshot)
                .where(
                    StagingFeedRankSnapshot.raw_feed_response_id.in_(
                        raw_feed_response_ids
                    )
                )
                .order_by(
                    StagingFeedRankSnapshot.raw_feed_response_id,
                    StagingFeedRankSnapshot.rank_position,
                )
            )

            staging_snapshots = session.scalars(stmt).all()

            assert len(staging_snapshots) == 6

            for raw_feed_response_id in raw_feed_response_ids:
                snapshots = [
                    snapshot
                    for snapshot in staging_snapshots
                    if snapshot.raw_feed_response_id == raw_feed_response_id
                ]

                assert len(snapshots) == 3
                assert [snapshot.item_id for snapshot in snapshots] == [101, 202, 303]
                assert [snapshot.rank_position for snapshot in snapshots] == [1, 2, 3]
                assert {snapshot.feed_name for snapshot in snapshots} == {"topstories"}
                assert {snapshot.observed_at for snapshot in snapshots} == {
                    raw_by_id[raw_feed_response_id].fetched_at
                }

    finally:
        # Eliminar staging records antes de eliminar el raw ingestion
        with session_factory.begin() as session:
            if raw_feed_response_ids:
                session.execute(
                    delete(StagingFeedRankSnapshot).where(
                        StagingFeedRankSnapshot.raw_feed_response_id.in_(
                            raw_feed_response_ids
                        )
                    )
                )

                session.execute(
                    delete(RawFeedResponse).where(
                        RawFeedResponse.raw_feed_response_id.in_(raw_feed_response_ids)
                    )
                )
