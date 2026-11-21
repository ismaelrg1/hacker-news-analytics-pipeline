from datetime import datetime

from sqlalchemy.orm import Session

from hacker_news_pipeline.db.orm_models import RawFeedResponse, RawItemResponse


class RawItemResponseRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_item_response(
        self,
        *,
        source_name: str,
        item_id: int,
        response_payload: dict[str, object],
        payload_hash: str,
        fetched_at: datetime,
    ) -> RawItemResponse:
        raw_item_response = RawItemResponse(
            source_name=source_name,
            item_id=item_id,
            response_payload=response_payload,
            payload_hash=payload_hash,
            fetched_at=fetched_at,
        )

        self._session.add(raw_item_response)
        self._session.flush()

        return raw_item_response


class RawFeedResponseRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_feed_response(
        self,
        *,
        source_name: str,
        feed_name: str,
        response_payload: list[int],
        payload_hash: str,
        fetched_at: datetime,
    ) -> RawFeedResponse:
        raw_feed_response = RawFeedResponse(
            source_name=source_name,
            feed_name=feed_name,
            response_payload=response_payload,
            payload_hash=payload_hash,
            fetched_at=fetched_at,
        )

        self._session.add(raw_feed_response)
        self._session.flush()

        return raw_feed_response
