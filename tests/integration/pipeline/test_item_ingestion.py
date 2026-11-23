from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from sqlalchemy import delete, select
from sqlalchemy.engine import Engine

from hacker_news_pipeline.api.hacker_news_client import (
    HackerNewsClient,
    HackerNewsItemFetch,
)
from hacker_news_pipeline.api.schemas import HackerNewsItemResponse
from hacker_news_pipeline.db.orm_models import (
    RawItemResponse,
    StagingItemVersion,
)
from hacker_news_pipeline.db.session import create_session_factory
from hacker_news_pipeline.pipeline.hashing import calculate_payload_hash
from hacker_news_pipeline.pipeline.item_ingestion import ingest_item

pytestmark = pytest.mark.integration


def test_ingest_item_persists_raw_item_and_version(engine: Engine) -> None:
    # Arrange: preparar una respuesta simulada
    item_id = 8863

    raw_payload: dict[str, object] = {
        "id": item_id,
        "type": "story",
        "by": "test_author",
        "time": 1768435200,
        "title": "A test story",
        "text": "Story body",
        "url": "https://example.com/story",
        "score": 42,
        "descendants": 5,
    }

    validated_item = HackerNewsItemResponse.model_validate(
        raw_payload,
    )

    client = Mock(spec=HackerNewsClient)
    client.get_item.return_value = HackerNewsItemFetch(
        raw_payload=raw_payload,
        item=validated_item,
    )

    session_factory = create_session_factory(engine)

    raw_item_response_id: int | None = None

    try:
        # Act: Ejecutar el proceso de ingestion
        result = ingest_item(
            client=client,
            session_factory=session_factory,
            item_id=item_id,
        )

        raw_item_response_id = result.raw_item_response_id

        assert result.item_id == item_id
        assert result.raw_item_response_id is not None
        assert result.raw_item_response_id == raw_item_response_id

        client.get_item.assert_called_once_with(item_id=item_id)

        assert result.hn_item_version_id is not None

        # Consultar de nuevo PostgreSQL con una sesion independiente.
        with session_factory() as session:
            raw = session.get(RawItemResponse, raw_item_response_id)

            assert raw is not None
            assert raw.source_name == "hacker_news"
            assert raw.item_id == item_id
            assert raw.response_payload == raw_payload
            assert raw.payload_hash == calculate_payload_hash(raw_payload)
            assert raw.fetched_at is not None

            # Verificar staging
            staging_item = session.get(
                StagingItemVersion,
                result.hn_item_version_id,
            )

            assert staging_item is not None

            assert staging_item.item_id == item_id
            assert staging_item.payload_hash == calculate_payload_hash(raw_payload)
            assert staging_item.first_raw_response_id == raw_item_response_id
            assert staging_item.first_seen_at == raw.fetched_at
            assert staging_item.last_seen_at == raw.fetched_at
            assert staging_item.item_type == "story"
            assert staging_item.author_username == "test_author"
            assert staging_item.title == "A test story"
            assert staging_item.text == "Story body"
            assert staging_item.url == "https://example.com/story"
            assert staging_item.score == 42
            assert staging_item.descendants_count == 5
            assert staging_item.is_deleted is False
            assert staging_item.is_dead is False

            assert validated_item.created_at_unix is not None

            expected_created_at = datetime.fromtimestamp(
                validated_item.created_at_unix,
                tz=UTC,
            )

            assert staging_item.created_at == expected_created_at

    finally:
        # Eliminar staging records antes de eliminar el raw ingestion
        if raw_item_response_id is not None:
            with session_factory.begin() as session:
                session.execute(
                    delete(StagingItemVersion).where(
                        StagingItemVersion.first_raw_response_id == raw_item_response_id
                    )
                )

                session.execute(
                    delete(RawItemResponse).where(
                        RawItemResponse.raw_item_response_id == raw_item_response_id
                    )
                )


def test_ingest_item_updates_existing_staging_version_for_same_payload(
    engine: Engine,
) -> None:
    # Arrange
    item_id = 8863
    raw_payload: dict[str, object] = {
        "id": item_id,
        "type": "story",
        "by": "test_author",
        "time": 1768435200,
        "title": "A test story",
        "text": "Story body",
        "url": "https://example.com/story",
        "score": 42,
        "descendants": 5,
    }

    validated_item = HackerNewsItemResponse.model_validate(
        raw_payload,
    )

    client = Mock(spec=HackerNewsClient)
    client.get_item.return_value = HackerNewsItemFetch(
        raw_payload=raw_payload,
        item=validated_item,
    )

    session_factory = create_session_factory(engine)
    raw_item_response_ids: list[int] = []

    try:
        # Act
        first_result = ingest_item(
            client=client,
            session_factory=session_factory,
            item_id=item_id,
        )
        raw_item_response_ids.append(first_result.raw_item_response_id)

        second_result = ingest_item(
            client=client,
            session_factory=session_factory,
            item_id=item_id,
        )
        raw_item_response_ids.append(second_result.raw_item_response_id)

        # Assert: pipeline results
        assert first_result.raw_item_response_id != second_result.raw_item_response_id
        assert first_result.hn_item_version_id == second_result.hn_item_version_id
        assert client.get_item.call_count == 2

        # Assert: persisted raw and staging data
        with session_factory() as session:
            raw_statement = select(RawItemResponse).where(
                RawItemResponse.raw_item_response_id.in_(raw_item_response_ids)
            )

            persisted_raw_responses = session.scalars(raw_statement).all()

            assert len(persisted_raw_responses) == 2

            raw_by_id = {
                raw.raw_item_response_id: raw for raw in persisted_raw_responses
            }

            assert set(raw_by_id) == set(raw_item_response_ids)

            for raw in persisted_raw_responses:
                assert raw.item_id == item_id
                assert raw.response_payload == raw_payload
                assert raw.payload_hash == calculate_payload_hash(raw_payload)

            staging_version = session.get(
                StagingItemVersion,
                first_result.hn_item_version_id,
            )

            assert staging_version is not None
            assert (
                staging_version.first_raw_response_id
                == first_result.raw_item_response_id
            )
            assert (
                staging_version.first_seen_at
                == raw_by_id[first_result.raw_item_response_id].fetched_at
            )
            assert (
                staging_version.last_seen_at
                == raw_by_id[second_result.raw_item_response_id].fetched_at
            )
            assert staging_version.score == 42

    finally:
        if raw_item_response_ids:
            with session_factory.begin() as session:
                session.execute(
                    delete(StagingItemVersion).where(
                        StagingItemVersion.first_raw_response_id.in_(
                            raw_item_response_ids
                        )
                    )
                )

                session.execute(
                    delete(RawItemResponse).where(
                        RawItemResponse.raw_item_response_id.in_(raw_item_response_ids)
                    )
                )


def test_ingest_item_creates_new_staging_version_when_payload_changes(
    engine: Engine,
) -> None:
    # Arrange
    item_id = 8863

    first_raw_payload: dict[str, object] = {
        "id": item_id,
        "type": "story",
        "by": "test_author",
        "time": 1768435200,
        "title": "A test story",
        "text": "Story body",
        "url": "https://example.com/story",
        "score": 42,
        "descendants": 5,
    }

    second_raw_payload = {
        **first_raw_payload,
        "score": 43,
    }

    first_validated_item = HackerNewsItemResponse.model_validate(
        first_raw_payload,
    )
    second_validated_item = HackerNewsItemResponse.model_validate(
        second_raw_payload,
    )

    client = Mock(spec=HackerNewsClient)
    client.get_item.side_effect = [
        HackerNewsItemFetch(
            raw_payload=first_raw_payload,
            item=first_validated_item,
        ),
        HackerNewsItemFetch(
            raw_payload=second_raw_payload,
            item=second_validated_item,
        ),
    ]

    session_factory = create_session_factory(engine)
    raw_item_response_ids: list[int] = []

    try:
        # Act
        first_result = ingest_item(
            client=client,
            session_factory=session_factory,
            item_id=item_id,
        )
        raw_item_response_ids.append(first_result.raw_item_response_id)

        second_result = ingest_item(
            client=client,
            session_factory=session_factory,
            item_id=item_id,
        )
        raw_item_response_ids.append(second_result.raw_item_response_id)

        # Assert: pipeline results
        assert first_result.raw_item_response_id != second_result.raw_item_response_id
        assert first_result.hn_item_version_id != second_result.hn_item_version_id
        assert client.get_item.call_count == 2

        # Assert: persisted raw and staging data
        with session_factory() as session:
            raw_statement = select(RawItemResponse).where(
                RawItemResponse.raw_item_response_id.in_(raw_item_response_ids)
            )

            persisted_raw_responses = session.scalars(raw_statement).all()

            assert len(persisted_raw_responses) == 2

            raw_by_id = {
                raw.raw_item_response_id: raw for raw in persisted_raw_responses
            }

            assert (
                raw_by_id[first_result.raw_item_response_id].response_payload
                == first_raw_payload
            )
            assert (
                raw_by_id[second_result.raw_item_response_id].response_payload
                == second_raw_payload
            )

            staging_statement = (
                select(StagingItemVersion)
                .where(
                    StagingItemVersion.hn_item_version_id.in_(
                        [
                            first_result.hn_item_version_id,
                            second_result.hn_item_version_id,
                        ]
                    )
                )
                .order_by(StagingItemVersion.hn_item_version_id)
            )

            persisted_versions = session.scalars(staging_statement).all()

            assert len(persisted_versions) == 2

            versions_by_id = {
                version.hn_item_version_id: version for version in persisted_versions
            }

            first_version = versions_by_id[first_result.hn_item_version_id]
            second_version = versions_by_id[second_result.hn_item_version_id]

            assert (
                first_version.first_raw_response_id == first_result.raw_item_response_id
            )
            assert (
                second_version.first_raw_response_id
                == second_result.raw_item_response_id
            )

            assert first_version.score == 42
            assert second_version.score == 43
            assert first_version.payload_hash != second_version.payload_hash

    finally:
        if raw_item_response_ids:
            with session_factory.begin() as session:
                session.execute(
                    delete(StagingItemVersion).where(
                        StagingItemVersion.first_raw_response_id.in_(
                            raw_item_response_ids
                        )
                    )
                )

                session.execute(
                    delete(RawItemResponse).where(
                        RawItemResponse.raw_item_response_id.in_(raw_item_response_ids)
                    )
                )
