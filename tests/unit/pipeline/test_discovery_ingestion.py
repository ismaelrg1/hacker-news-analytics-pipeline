from unittest.mock import Mock, call

import pytest

from hacker_news_pipeline.api.hacker_news_client import HackerNewsClient
from hacker_news_pipeline.pipeline import discovery_ingestion
from hacker_news_pipeline.pipeline.feed_ingestion import FeedIngestionResult
from hacker_news_pipeline.pipeline.item_ingestion import ItemIngestionResult


def test_ingest_discovery_feeds_deduplicates_item_ids_preserving_first_seen_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    topstories = FeedIngestionResult(
        raw_feed_response_id=1,
        feed_name="topstories",
        item_ids=(10, 20, 30),
        fetched_item_count=3,
        inserted_rank_snapshot_count=3,
    )
    newstories = FeedIngestionResult(
        raw_feed_response_id=2,
        feed_name="newstories",
        item_ids=(20, 40),
        fetched_item_count=2,
        inserted_rank_snapshot_count=2,
    )
    beststories = FeedIngestionResult(
        raw_feed_response_id=3,
        feed_name="beststories",
        item_ids=(30, 50),
        fetched_item_count=2,
        inserted_rank_snapshot_count=2,
    )

    client = Mock(spec=HackerNewsClient)

    session_factory = Mock()

    ingest_feed_mock = Mock(
        side_effect=[
            topstories,
            newstories,
            beststories,
        ]
    )

    def build_item_result(
        *, client: HackerNewsClient, session_factory: object, item_id: int
    ) -> ItemIngestionResult:
        return ItemIngestionResult(
            item_id=item_id,
            raw_item_response_id=item_id + 1_000,
            hn_item_version_id=item_id + 2_000,
        )

    ingest_item_mock = Mock(side_effect=build_item_result)

    monkeypatch.setattr(
        discovery_ingestion,
        "ingest_feed",
        ingest_feed_mock,
    )

    monkeypatch.setattr(
        discovery_ingestion,
        "ingest_item",
        ingest_item_mock,
    )

    result = discovery_ingestion.ingest_discovery_feeds(
        client=client,
        session_factory=session_factory,
        feed_names=("topstories", "newstories", "beststories"),
    )

    assert ingest_feed_mock.call_args_list == [
        call(
            client=client,
            session_factory=session_factory,
            feed_name="topstories",
        ),
        call(
            client=client,
            session_factory=session_factory,
            feed_name="newstories",
        ),
        call(
            client=client,
            session_factory=session_factory,
            feed_name="beststories",
        ),
    ]

    assert ingest_item_mock.call_args_list == [
        call(
            client=client,
            session_factory=session_factory,
            item_id=10,
        ),
        call(
            client=client,
            session_factory=session_factory,
            item_id=20,
        ),
        call(
            client=client,
            session_factory=session_factory,
            item_id=30,
        ),
        call(
            client=client,
            session_factory=session_factory,
            item_id=40,
        ),
        call(
            client=client,
            session_factory=session_factory,
            item_id=50,
        ),
    ]

    assert result.unique_item_count == 5
    assert result.feed_results == (
        topstories,
        newstories,
        beststories,
    )
    assert [item_result.item_id for item_result in result.item_results] == [
        10,
        20,
        30,
        40,
        50,
    ]


def test_ingest_discovery_feeds_propagates_item_ingestion_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    topstories = FeedIngestionResult(
        raw_feed_response_id=1,
        feed_name="topstories",
        item_ids=(10, 20, 30),
        fetched_item_count=3,
        inserted_rank_snapshot_count=3,
    )

    client = Mock(spec=HackerNewsClient)

    session_factory = Mock()

    ingest_feed_mock = Mock(return_value=topstories)

    first_item_result = ItemIngestionResult(
        item_id=10,
        raw_item_response_id=1_010,
        hn_item_version_id=2_010,
    )

    ingest_item_mock = Mock(
        side_effect=[
            first_item_result,
            RuntimeError("Item ingestion failed"),
        ]
    )

    monkeypatch.setattr(
        discovery_ingestion,
        "ingest_feed",
        ingest_feed_mock,
    )

    monkeypatch.setattr(
        discovery_ingestion,
        "ingest_item",
        ingest_item_mock,
    )

    with pytest.raises(RuntimeError, match="Item ingestion failed"):
        discovery_ingestion.ingest_discovery_feeds(
            client=client, session_factory=session_factory, feed_names=("topstories",)
        )

    assert ingest_feed_mock.call_args_list == [
        call(
            client=client,
            session_factory=session_factory,
            feed_name="topstories",
        ),
    ]

    assert ingest_item_mock.call_args_list == [
        call(
            client=client,
            session_factory=session_factory,
            item_id=10,
        ),
        call(
            client=client,
            session_factory=session_factory,
            item_id=20,
        ),
    ]
