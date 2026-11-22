from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator


class HackerNewsItemResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    item_id: int = Field(alias="id", gt=0)
    item_type: (
        Literal[
            "job",
            "story",
            "comment",
            "poll",
            "pollopt",
        ]
        | None
    ) = Field(alias="type", default=None)
    author_username: str | None = Field(alias="by", default=None)
    created_at_unix: int | None = Field(alias="time", default=None)
    is_deleted: bool = Field(alias="deleted", default=False)
    is_dead: bool = Field(alias="dead", default=False)
    parent_item_id: int | None = Field(alias="parent", gt=0, default=None)
    poll_id: int | None = Field(alias="poll", gt=0, default=None)
    kids: list[int] = Field(default_factory=list)
    parts: list[int] = Field(default_factory=list)
    title: str | None = Field(default=None)
    text: str | None = Field(default=None)
    url: str | None = Field(default=None)
    score: int | None = Field(ge=0, default=None)
    descendants_count: int | None = Field(alias="descendants", ge=0, default=None)


FeedItemId = Annotated[int, Field(gt=0)]
NonEmptyFeedItemIds = Annotated[
    list[FeedItemId],
    Field(min_length=1),
]


class HackerNewsFeedResponse(RootModel[NonEmptyFeedItemIds]):
    @model_validator(mode="after")
    def validate_no_duplicate_item_ids(self) -> Self:
        if len(self.root) != len(set(self.root)):
            raise ValueError("Feed response contains duplicate item IDs")
        return self
