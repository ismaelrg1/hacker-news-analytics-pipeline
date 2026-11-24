import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from hacker_news_pipeline.api.hacker_news_client import HackerNewsClient
from hacker_news_pipeline.db.raw_repositories import RawFeedResponseRepository
from hacker_news_pipeline.db.staging_repositories import (
    StagingFeedRankSnapshotRepository,
)
from hacker_news_pipeline.pipeline.hashing import calculate_payload_hash

HACKER_NEWS_SOURCE_NAME = "hacker_news"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeedIngestionResult:
    raw_feed_response_id: int
    feed_name: str
    item_ids: tuple[int, ...]
    fetched_item_count: int
    inserted_rank_snapshot_count: int


def ingest_feed(
    *,
    client: HackerNewsClient,
    session_factory: sessionmaker[Session],
    feed_name: str,
) -> FeedIngestionResult:

    fetched_feed = client.get_feed(feed_name=feed_name)

    logger.info(
        "Fetched Hacker News feed | feed_name=%s item_count=%s",
        feed_name,
        len(fetched_feed.feed.root),
    )

    fetched_at = datetime.now(UTC)

    payload_hash = calculate_payload_hash(fetched_feed.raw_payload)

    item_ids = tuple(fetched_feed.feed.root)

    with session_factory.begin() as session:
        raw_repository = RawFeedResponseRepository(session=session)

        staging_repository = StagingFeedRankSnapshotRepository(session=session)

        raw_feed_response = raw_repository.create_feed_response(
            source_name=HACKER_NEWS_SOURCE_NAME,
            feed_name=feed_name,
            response_payload=fetched_feed.raw_payload,
            payload_hash=payload_hash,
            fetched_at=fetched_at,
        )

        raw_feed_response_id = raw_feed_response.raw_feed_response_id

        inserted_rank_snapshot_count = (
            staging_repository.insert_rank_snapshots_if_absent(
                raw_feed_response=raw_feed_response,
            )
        )

    logger.info(
        "Persisted Hacker News feed | "
        "feed_name=%s raw_feed_response_id=%s "
        "inserted_rank_snapshot_count=%s",
        feed_name,
        raw_feed_response_id,
        inserted_rank_snapshot_count,
    )

    return FeedIngestionResult(
        raw_feed_response_id=raw_feed_response_id,
        feed_name=feed_name,
        item_ids=item_ids,
        fetched_item_count=len(item_ids),
        inserted_rank_snapshot_count=inserted_rank_snapshot_count,
    )
