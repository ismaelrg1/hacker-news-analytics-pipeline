from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hacker_news_pipeline.db.base import Base


class RawFeedResponse(Base):
    __tablename__ = "hn_feed_responses"
    __table_args__ = (
        CheckConstraint(
            "payload_hash ~ '^[0-9a-f]{64}$'",
            name="chk_hn_feed_responses_payload_hash_format",
        ),
        CheckConstraint(
            "feed_name IN ('newstories', 'topstories', 'beststories')",
            name="chk_hn_feed_responses_supported_feed_name",
        ),
        {"schema": "raw"},
    )

    raw_feed_response_id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )

    source_name: Mapped[str] = mapped_column(String(50), nullable=False)

    feed_name: Mapped[str] = mapped_column(String(20), nullable=False)

    response_payload: Mapped[list[int]] = mapped_column(JSONB, nullable=False)

    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # relationship
    feed_rank_snapshots: Mapped[list["StagingFeedRankSnapshot"]] = relationship(
        back_populates="raw_feed_response",
    )


class RawItemResponse(Base):
    __tablename__ = "hn_item_responses"
    __table_args__ = (
        CheckConstraint(
            "payload_hash ~ '^[0-9a-f]{64}$'",
            name="chk_hn_item_responses_payload_hash_format",
        ),
        {"schema": "raw"},
    )

    raw_item_response_id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )

    source_name: Mapped[str] = mapped_column(String(50), nullable=False)

    item_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    response_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)

    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # relationhips
    item_version: Mapped["StagingItemVersion | None"] = relationship(
        back_populates="first_raw_response", uselist=False
    )


class StagingItemVersion(Base):
    __tablename__ = "item_versions"
    __table_args__ = (
        CheckConstraint(
            "payload_hash ~ '^[0-9a-f]{64}$'",
            name="chk_item_versions_payload_hash_format",
        ),
        CheckConstraint(
            "score IS NULL OR score >= 0",
            name="chk_item_versions_null_or_positive_score",
        ),
        CheckConstraint(
            "descendants_count IS NULL OR descendants_count >= 0",
            name="chk_item_versions_null_or_positive_descendants_count",
        ),
        CheckConstraint(
            "last_seen_at >= first_seen_at",
            name="chk_item_versions_last_seen_at_after_first_seen_at",
        ),
        UniqueConstraint(
            "item_id",
            "payload_hash",
            name="uq_item_version_item_id_payload",
        ),
        CheckConstraint(
            "item_type IS NULL OR item_type IN "
            "('job', 'story', 'comment', 'poll', 'pollopt')",
            name="chk_item_versions_supported_item_type",
        ),
        UniqueConstraint(
            "first_raw_response_id",
            name="uq_item_versions_first_raw_response_id",
        ),
        {"schema": "staging"},
    )

    hn_item_version_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    item_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    first_raw_response_id: Mapped[int] = mapped_column(
        ForeignKey("raw.hn_item_responses.raw_item_response_id"), nullable=False
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    item_type: Mapped[str | None] = mapped_column(String(10), nullable=True)

    author_username: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    is_dead: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    parent_item_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    title: Mapped[str | None] = mapped_column(Text, nullable=True)

    text: Mapped[str | None] = mapped_column(Text, nullable=True)

    url: Mapped[str | None] = mapped_column(Text, nullable=True)

    score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    descendants_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # relationship
    first_raw_response: Mapped["RawItemResponse"] = relationship(
        back_populates="item_version"
    )


class StagingFeedRankSnapshot(Base):
    __tablename__ = "feed_rank_snapshots"
    __table_args__ = (
        CheckConstraint(
            "rank_position > 0",
            name="chk_feed_rank_snapshots_positive_rank_position",
        ),
        CheckConstraint(
            "feed_name IN ('newstories', 'topstories', 'beststories')",
            name="chk_feed_rank_snapshots_supported_feed_name",
        ),
        UniqueConstraint(
            "raw_feed_response_id",
            "rank_position",
            name="uq_feed_rank_snapshots_feed_response_rank_position",
        ),
        UniqueConstraint(
            "raw_feed_response_id",
            "item_id",
            name="uq_feed_rank_snapshots_feed_response_item_id",
        ),
        {"schema": "staging"},
    )

    hn_feed_rank_snapshot_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    raw_feed_response_id: Mapped[int] = mapped_column(
        ForeignKey("raw.hn_feed_responses.raw_feed_response_id"), nullable=False
    )

    feed_name: Mapped[str] = mapped_column(String(20), nullable=False)

    item_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    rank_position: Mapped[int] = mapped_column(Integer, nullable=False)

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # relationship
    raw_feed_response: Mapped["RawFeedResponse"] = relationship(
        back_populates="feed_rank_snapshots",
    )
