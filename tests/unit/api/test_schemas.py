import pytest
from pydantic import ValidationError

from hacker_news_pipeline.api.schemas import (
    HackerNewsFeedResponse,
    HackerNewsItemResponse,
)


def build_story_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": 8863,
        "type": "story",
        "by": "dhouston",
        "time": 1175714200,
        "score": 111,
        "title": "My YC app: Dropbox - Throw away your USB drive",
        "url": "http://www.getdropbox.com/u/2/screencast.html",
        "kids": [8952, 9224],
        "descendants": 71,
    }
    payload.update(overrides)
    return payload


def test_item_response_validate_complete_story() -> None:
    result = HackerNewsItemResponse.model_validate(build_story_payload())

    assert result.item_id == 8863
    assert result.author_username == "dhouston"
    assert result.created_at_unix == 1175714200
    assert result.item_type == "story"
    assert result.score == 111
    assert result.kids == [8952, 9224]
    assert result.descendants_count == 71


def test_item_response_accepts_minimum_valid_payload() -> None:
    result = HackerNewsItemResponse.model_validate({"id": 123})

    assert result.item_id == 123
    assert result.item_type is None
    assert result.author_username is None
    assert result.created_at_unix is None
    assert result.is_deleted is False
    assert result.is_dead is False
    assert result.kids == []
    assert result.parts == []


def test_item_response_rejects_missing_item_id() -> None:

    with pytest.raises(ValidationError):
        HackerNewsItemResponse.model_validate({})


@pytest.mark.parametrize("item_type", ["video", " ", ""])
def test_item_response_rejects_unknown_item_type(item_type: str | None) -> None:

    with pytest.raises(ValidationError):
        HackerNewsItemResponse.model_validate(build_story_payload(type=item_type))


@pytest.mark.parametrize("item_id", [0, -1])
def test_item_response_rejects_non_positive_item_id(item_id: int) -> None:

    with pytest.raises(ValidationError):
        HackerNewsItemResponse.model_validate(build_story_payload(id=item_id))


@pytest.mark.parametrize("item_type", ["job", "comment", "poll", "pollopt"])
def test_item_response_accepts_supported_item_types(item_type: int) -> None:

    result = HackerNewsItemResponse.model_validate(build_story_payload(type=item_type))

    assert result.item_type == item_type


def test_item_response_rejects_negative_score() -> None:

    with pytest.raises(ValidationError):
        HackerNewsItemResponse.model_validate({"id": 123, "score": -1})


def test_item_response_rejects_negative_descendants() -> None:

    with pytest.raises(ValidationError):
        HackerNewsItemResponse.model_validate({"id": 123, "descendants": -1})


def test_item_response_ignores_unknown_api_fields() -> None:
    result = HackerNewsItemResponse.model_validate(
        build_story_payload(
            future_hacker_news_field="a value not used by our pipeline",
        )
    )

    assert result.item_id == 8863
    assert "future_hacker_news_field" not in result.model_dump()


def test_feed_response_validates_positive_item_ids() -> None:
    payload = [1, 42, 999]

    result = HackerNewsFeedResponse.model_validate(payload)

    assert result.root == payload


@pytest.mark.parametrize(
    "invalid_payload",
    [
        [],
        [1, 0],
        [1, -4],
        [1, "not-an-id"],
    ],
)
def test_feed_response_rejects_invalid_item_ids(
    invalid_payload: object,
) -> None:
    with pytest.raises(ValidationError):
        HackerNewsFeedResponse.model_validate(invalid_payload)
