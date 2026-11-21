import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from hacker_news_pipeline.db.session import create_session_factory

pytestmark = pytest.mark.integration


def test_session_factory_can_execute_query(engine: Engine) -> None:
    session_factory = create_session_factory(engine)

    with session_factory() as db_session:
        result = db_session.execute(text("SELECT current_database()"))

        assert result.scalar_one() == "hacker_news_test"
