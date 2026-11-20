from dataclasses import dataclass

import httpx

from hacker_news_pipeline.api.schemas import (
    HackerNewsFeedResponse,
    HackerNewsItemResponse,
)
from hacker_news_pipeline.config import Settings


@dataclass(frozen=True)
class HackerNewsFeedFetch:
    raw_payload: list[int]
    feed: HackerNewsFeedResponse


@dataclass(frozen=True)
class HackerNewsItemFetch:
    raw_payload: dict[str, object]
    item: HackerNewsItemResponse


class HackerNewsClient:
    def __init__(
        self,
        http_client: httpx.Client,
        settings: Settings,
    ) -> None:
        self._http_client = http_client
        self._settings = settings

    def get_feed(self, *, feed_name: str) -> HackerNewsFeedFetch:
        url = f"{self._settings.hacker_news_base_url}/{feed_name}.json"

        response = self._http_client.get(
            url,
        )
        response.raise_for_status()

        raw_payload = response.json()

        feed = HackerNewsFeedResponse.model_validate(raw_payload)

        return HackerNewsFeedFetch(
            raw_payload=raw_payload,
            feed=feed,
        )

    def get_item(self, *, item_id: int) -> HackerNewsItemFetch:
        url = f"{self._settings.hacker_news_base_url}/item/{item_id}.json"

        response = self._http_client.get(
            url,
        )
        response.raise_for_status()

        raw_payload = response.json()

        item = HackerNewsItemResponse.model_validate(raw_payload)

        return HackerNewsItemFetch(
            raw_payload=raw_payload,
            item=item,
        )
