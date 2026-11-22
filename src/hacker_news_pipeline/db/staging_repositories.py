from datetime import datetime

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from hacker_news_pipeline.api.schemas import HackerNewsItemResponse
from hacker_news_pipeline.db.orm_models import RawItemResponse, StagingItemVersion


class StagingItemVersionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_item_version(
        self,
        *,
        raw_item_response: RawItemResponse,
        item: HackerNewsItemResponse,
        created_at: datetime | None,
    ) -> StagingItemVersion:
        if raw_item_response.item_id != item.item_id:
            raise ValueError(
                "Raw item response and validated item must have the same item_id"
            )

        values = {
            "item_id": item.item_id,
            "payload_hash": raw_item_response.payload_hash,
            "first_raw_response_id": raw_item_response.raw_item_response_id,
            "first_seen_at": raw_item_response.fetched_at,
            "last_seen_at": raw_item_response.fetched_at,
            "item_type": item.item_type,
            "author_username": item.author_username,
            "created_at": created_at,
            "is_deleted": item.is_deleted,
            "is_dead": item.is_dead,
            "parent_item_id": item.parent_item_id,
            "title": item.title,
            "text": item.text,
            "url": item.url,
            "score": item.score,
            "descendants_count": item.descendants_count,
        }

        insert_statement = insert(StagingItemVersion).values(values)

        upsert_statement = insert_statement.on_conflict_do_update(
            constraint="uq_item_version_item_id_payload",
            set_={
                "last_seen_at": func.greatest(
                    StagingItemVersion.last_seen_at,
                    insert_statement.excluded.last_seen_at,
                ),
            },
        ).returning(StagingItemVersion)

        result = self._session.execute(
            upsert_statement,
            execution_options={"populate_existing": True},
        )

        return result.scalar_one()
