from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from hacker_news_pipeline.api.hacker_news_client import HackerNewsClient
from hacker_news_pipeline.pipeline.feed_ingestion import (
    FeedIngestionResult,
    ingest_feed,
)
from hacker_news_pipeline.pipeline.item_ingestion import (
    ItemIngestionResult,
    ingest_item,
)


@dataclass(frozen=True)
class DiscoveryIngestionResult:
    feed_results: tuple[FeedIngestionResult, ...]
    item_results: tuple[ItemIngestionResult, ...]
    unique_item_count: int


def ingest_discovery_feeds(
    *,
    client: HackerNewsClient,
    session_factory: sessionmaker[Session],
    feed_names: Sequence[str],
) -> DiscoveryIngestionResult:
    feed_results: list[FeedIngestionResult] = []
    unique_item_ids: list[int] = []
    seen_item_ids: set[int] = set()

    for feed_name in feed_names:
        feed_result = ingest_feed(
            client=client,
            session_factory=session_factory,
            feed_name=feed_name,
        )

        feed_results.append(feed_result)

        for item_id in feed_result.item_ids:
            if item_id not in seen_item_ids:
                unique_item_ids.append(item_id)
                seen_item_ids.add(item_id)

    item_results: list[ItemIngestionResult] = []

    for item_id in unique_item_ids:
        item_result = ingest_item(
            client=client,
            session_factory=session_factory,
            item_id=item_id,
        )

        item_results.append(item_result)

    return DiscoveryIngestionResult(
        feed_results=tuple(feed_results),
        item_results=tuple(item_results),
        unique_item_count=len(unique_item_ids),
    )
