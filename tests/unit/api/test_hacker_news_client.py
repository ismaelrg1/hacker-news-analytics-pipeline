import httpx
import pytest
from pydantic import ValidationError

from hacker_news_pipeline.api.hacker_news_client import HackerNewsClient
from hacker_news_pipeline.api.schemas import (
    HackerNewsFeedResponse,
    HackerNewsItemResponse,
)
from hacker_news_pipeline.config import Settings

BASE_URL = "https://hacker-news.firebaseio.com/v0"
FEED_NAME = "newstories"
DATABASE_URL = (
    "postgresql+psycopg://test_user:test_password@localhost:5432/test_database"
)


# Fake settings without loading the real .env file.
@pytest.fixture
def settings() -> Settings:
    """Build settings for the HN client tests."""
    return Settings(hacker_news_base_url=BASE_URL, database_url=DATABASE_URL)


##############################################################
#                 Test Feed
##############################################################


# Valid API response payload.
@pytest.fixture
def sample_feed_payload() -> list[int]:
    return [123, 122, 234]


# Verifies the feed endpoint URL and returned data.
def test_get_feed_builds_expected_url(
    settings: Settings,
    sample_feed_payload: list[int],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"

        assert str(request.url) == (f"{BASE_URL}/{FEED_NAME}.json")

        return httpx.Response(200, json=sample_feed_payload)

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as http_client:
        client = HackerNewsClient(http_client=http_client, settings=settings)

        result = client.get_feed(feed_name=FEED_NAME)

    assert result.raw_payload == sample_feed_payload
    assert result.feed.root == sample_feed_payload
    assert isinstance(result.feed, HackerNewsFeedResponse)


def test_get_feed_raises_for_unsuccessful_http_response(
    settings: Settings,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"

        assert str(request.url) == (f"{BASE_URL}/{FEED_NAME}.json")

        return httpx.Response(404)

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as http_client:
        client = HackerNewsClient(http_client=http_client, settings=settings)

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            client.get_feed(feed_name=FEED_NAME)

    assert exc_info.value.response.status_code == 404


def test_get_feed_rejects_invalid_api_payload(
    settings: Settings,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"

        assert str(request.url) == (f"{BASE_URL}/{FEED_NAME}.json")

        return httpx.Response(200, json=[])

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as http_client:
        client = HackerNewsClient(http_client=http_client, settings=settings)

        with pytest.raises(ValidationError):
            client.get_feed(feed_name=FEED_NAME)


##############################################################
#                 Test Item
##############################################################
ITEM_ID = 8863


# Valid API response payload.
@pytest.fixture
def sample_item_payload() -> dict[str, object]:
    return {"id": 8863}


# Verifies the item endpoint URL and returned data.
def test_get_item_builds_expected_url(
    settings: Settings,
    sample_item_payload: dict[str, object],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"

        assert str(request.url) == (f"{BASE_URL}/item/{ITEM_ID}.json")

        return httpx.Response(200, json=sample_item_payload)

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as http_client:
        client = HackerNewsClient(http_client=http_client, settings=settings)

        result = client.get_item(item_id=ITEM_ID)

    assert result.raw_payload == sample_item_payload
    assert isinstance(result.item, HackerNewsItemResponse)
    assert result.item.item_id == ITEM_ID


def test_get_item_raises_for_unsuccessful_http_response(
    settings: Settings,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"

        assert str(request.url) == (f"{BASE_URL}/item/{ITEM_ID}.json")

        return httpx.Response(404)

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as http_client:
        client = HackerNewsClient(http_client=http_client, settings=settings)
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            client.get_item(item_id=ITEM_ID)

    assert exc_info.value.response.status_code == 404


def test_get_item_rejects_invalid_api_payload(
    settings: Settings,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"

        assert str(request.url) == (f"{BASE_URL}/item/{ITEM_ID}.json")

        return httpx.Response(200, json={})

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as http_client:
        client = HackerNewsClient(http_client=http_client, settings=settings)

        with pytest.raises(ValidationError):
            client.get_item(item_id=ITEM_ID)
