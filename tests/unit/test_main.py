from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

import hacker_news_pipeline.main as main_module
from hacker_news_pipeline.api.hacker_news_client import HackerNewsClient
from hacker_news_pipeline.main import build_argument_parser
from hacker_news_pipeline.pipeline.discovery_ingestion import DiscoveryIngestionResult


def test_parser_accepts_one_supported_feed() -> None:
    parser = build_argument_parser()

    args = parser.parse_args(["--feed", "topstories"])

    assert args.feed == ["topstories"]


def test_parser_accepts_multiple_supported_feeds_in_order() -> None:
    parser = build_argument_parser()

    args = parser.parse_args(
        [
            "--feed",
            "topstories",
            "--feed",
            "newstories",
            "--feed",
            "beststories",
        ]
    )

    assert args.feed == ["topstories", "newstories", "beststories"]


def test_parser_requires_at_least_one_feed() -> None:
    parser = build_argument_parser()

    with pytest.raises(SystemExit) as exc:
        parser.parse_args([])

    assert exc.value.code == 2


@pytest.mark.parametrize("invalid_feed", ["unknown", "jobstories", ""])
def test_parser_rejects_unsupported_feed(
    invalid_feed: str,
) -> None:
    parser = build_argument_parser()

    with pytest.raises(SystemExit) as exc:
        parser.parse_args(
            [
                "--feed",
                invalid_feed,
            ]
        )

    assert exc.value.code == 2


def test_main_runs_discovery_workflow_and_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = SimpleNamespace(
        log_level="INFO",
        database_url="postgresql+psycopg://test",
        http_timeout_seconds=10,
    )

    settings_constructor = Mock(return_value=settings)

    engine = Mock()
    session_factory = Mock()

    create_engine_mock = Mock(return_value=engine)
    create_session_factory_mock = Mock(return_value=session_factory)

    http_client = Mock()

    http_client_context_manager = MagicMock()
    http_client_context_manager.__enter__.return_value = http_client
    http_client_context_manager.__exit__.return_value = False

    httpx_client_constructor = Mock(return_value=http_client_context_manager)

    hacker_news_client = Mock(spec=HackerNewsClient)

    hacker_news_client_constructor = Mock(return_value=hacker_news_client)

    discovery_result = DiscoveryIngestionResult(
        feed_results=(),
        item_results=(),
        unique_item_count=0,
    )

    ingest_discovery_feeds_mock = Mock(return_value=discovery_result)

    logger = Mock()

    configure_logging_mock = Mock()

    monkeypatch.setattr(
        main_module,
        "Settings",
        settings_constructor,
    )
    monkeypatch.setattr(
        main_module,
        "configure_logging",
        configure_logging_mock,
    )
    monkeypatch.setattr(
        main_module,
        "create_database_engine",
        create_engine_mock,
    )
    monkeypatch.setattr(
        main_module,
        "create_session_factory",
        create_session_factory_mock,
    )
    monkeypatch.setattr(
        main_module,
        "HackerNewsClient",
        hacker_news_client_constructor,
    )
    monkeypatch.setattr(
        main_module,
        "ingest_discovery_feeds",
        ingest_discovery_feeds_mock,
    )
    monkeypatch.setattr(
        main_module,
        "logger",
        logger,
    )
    monkeypatch.setattr(
        main_module.httpx,
        "Client",
        httpx_client_constructor,
    )

    result = main_module.main(
        ["--feed", "topstories"],
    )

    assert result == 0

    settings_constructor.assert_called_once_with()
    configure_logging_mock.assert_called_once_with("INFO")

    create_engine_mock.assert_called_once_with("postgresql+psycopg://test")
    create_session_factory_mock.assert_called_once_with(engine)

    httpx_client_constructor.assert_called_once_with(timeout=10)

    hacker_news_client_constructor.assert_called_once_with(
        http_client=http_client,
        settings=settings,
    )

    ingest_discovery_feeds_mock.assert_called_once_with(
        client=hacker_news_client,
        session_factory=session_factory,
        feed_names=["topstories"],
    )

    engine.dispose.assert_called_once()
    logger.info.assert_called_once()


def test_main_returns_one_and_disposes_engine_when_workflow_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = SimpleNamespace(
        log_level="INFO",
        database_url="postgresql+psycopg://test",
        http_timeout_seconds=10,
    )

    settings_constructor = Mock(return_value=settings)

    engine = Mock()
    session_factory = Mock()

    create_engine_mock = Mock(return_value=engine)
    create_session_factory_mock = Mock(
        return_value=session_factory,
    )

    http_client = Mock()

    http_client_context_manager = MagicMock()
    http_client_context_manager.__enter__.return_value = http_client
    http_client_context_manager.__exit__.return_value = False

    httpx_client_constructor = Mock(
        return_value=http_client_context_manager,
    )

    hacker_news_client = Mock(spec=HackerNewsClient)
    hacker_news_client_constructor = Mock(
        return_value=hacker_news_client,
    )

    ingest_discovery_feeds_mock = Mock(
        side_effect=RuntimeError("Pipeline failure"),
    )

    logger = Mock()
    configure_logging_mock = Mock()

    monkeypatch.setattr(
        main_module,
        "Settings",
        settings_constructor,
    )
    monkeypatch.setattr(
        main_module,
        "configure_logging",
        configure_logging_mock,
    )
    monkeypatch.setattr(
        main_module,
        "create_database_engine",
        create_engine_mock,
    )
    monkeypatch.setattr(
        main_module,
        "create_session_factory",
        create_session_factory_mock,
    )
    monkeypatch.setattr(
        main_module,
        "HackerNewsClient",
        hacker_news_client_constructor,
    )
    monkeypatch.setattr(
        main_module,
        "ingest_discovery_feeds",
        ingest_discovery_feeds_mock,
    )
    monkeypatch.setattr(
        main_module,
        "logger",
        logger,
    )
    monkeypatch.setattr(
        main_module.httpx,
        "Client",
        httpx_client_constructor,
    )

    result = main_module.main(
        ["--feed", "topstories"],
    )

    assert result == 1

    ingest_discovery_feeds_mock.assert_called_once_with(
        client=hacker_news_client,
        session_factory=session_factory,
        feed_names=["topstories"],
    )

    engine.dispose.assert_called_once()
    logger.exception.assert_called_once_with("Pipeline failed")
    logger.info.assert_not_called()
