import argparse
import logging
from collections.abc import Sequence

import httpx
from sqlalchemy.engine import Engine

from hacker_news_pipeline.api.hacker_news_client import HackerNewsClient
from hacker_news_pipeline.config import Settings
from hacker_news_pipeline.db.session import (
    create_database_engine,
    create_session_factory,
)
from hacker_news_pipeline.logging_config import configure_logging
from hacker_news_pipeline.pipeline.discovery_ingestion import ingest_discovery_feeds

logger = logging.getLogger(__name__)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hacker News data pipeline.")

    parser.add_argument(
        "--feed",
        type=str,
        action="append",
        required=True,
        choices=("newstories", "topstories", "beststories"),
        help="One or more feed names.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_argument_parser()

    arguments = parser.parse_args(argv)

    engine: Engine | None = None

    try:
        settings = Settings()

        configure_logging(settings.log_level)

        engine = create_database_engine(settings.database_url)

        session_factory = create_session_factory(engine)

        with httpx.Client(timeout=settings.http_timeout_seconds) as http_client:
            client = HackerNewsClient(
                http_client=http_client,
                settings=settings,
            )

            result = ingest_discovery_feeds(
                client=client,
                session_factory=session_factory,
                feed_names=arguments.feed,
            )

        logger.info(
            "Pipeline completed | feed_count=%s "
            "ingested_item_count=%s unique_item_count=%s",
            len(result.feed_results),
            len(result.item_results),
            result.unique_item_count,
        )

        return 0
    except Exception:
        logger.exception("Pipeline failed")
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
