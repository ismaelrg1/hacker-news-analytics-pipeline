import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from hacker_news_pipeline.api.hacker_news_client import HackerNewsClient
from hacker_news_pipeline.db.raw_repositories import RawItemResponseRepository
from hacker_news_pipeline.db.staging_repositories import (
    StagingItemVersionRepository,
)
from hacker_news_pipeline.pipeline.hashing import calculate_payload_hash

HACKER_NEWS_SOURCE_NAME = "hacker_news"

logger = logging.getLogger(__name__)


def _unix_to_datetime(created_at_unix: int | None) -> datetime | None:
    if created_at_unix is None:
        return None

    return datetime.fromtimestamp(created_at_unix, tz=UTC)


@dataclass(frozen=True)
class ItemIngestionResult:
    item_id: int
    raw_item_response_id: int
    hn_item_version_id: int


def ingest_item(
    *,
    client: HackerNewsClient,
    session_factory: sessionmaker[Session],
    item_id: int,
) -> ItemIngestionResult:
    fetched_item = client.get_item(item_id=item_id)

    logger.info(
        "Fetched Hacker News item | item_id=%s item_type=%s",
        item_id,
        fetched_item.item.item_type,
    )

    fetched_at = datetime.now(UTC)

    payload_hash = calculate_payload_hash(fetched_item.raw_payload)

    with session_factory.begin() as session:
        raw_repository = RawItemResponseRepository(session=session)

        staging_repository = StagingItemVersionRepository(session=session)

        raw_item_response = raw_repository.create_item_response(
            source_name=HACKER_NEWS_SOURCE_NAME,
            item_id=item_id,
            response_payload=fetched_item.raw_payload,
            payload_hash=payload_hash,
            fetched_at=fetched_at,
        )

        raw_item_response_id = raw_item_response.raw_item_response_id

        staging_item_version = staging_repository.upsert_item_version(
            raw_item_response=raw_item_response,
            item=fetched_item.item,
            created_at=_unix_to_datetime(fetched_item.item.created_at_unix),
        )

        hn_item_version_id = staging_item_version.hn_item_version_id

    logger.info(
        "Persisted Hacker News item | "
        "item_id=%s raw_item_response_id=%s "
        "hn_item_version_id=%s",
        item_id,
        raw_item_response_id,
        hn_item_version_id,
    )

    return ItemIngestionResult(
        raw_item_response_id=raw_item_response_id,
        item_id=item_id,
        hn_item_version_id=hn_item_version_id,
    )
