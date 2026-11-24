# Hacker News Analytics Pipeline

Local pipeline that ingests public Hacker News discovery feeds into PostgreSQL
while preserving the API history needed for later analytics.

The current implementation focuses on a reliable ingestion foundation. dbt
models, analytical marts, and Airflow orchestration are deliberately the next
stages of the project, not features that already exist.

## Current architecture

```text
Hacker News API
        |
        v
Python CLI + httpx + Pydantic validation
        |
        +--> feed responses
        |      -> raw.hn_feed_responses
        |      -> staging.feed_rank_snapshots
        |
        +--> item responses
               -> raw.hn_item_responses
               -> staging.item_versions
```

`ingest_discovery_feeds` coordinates the workflow:

1. Fetch each requested feed (`newstories`, `topstories`, or `beststories`).
2. Persist its complete response as a raw observation.
3. Expand its ordered item IDs into rank snapshots.
4. Deduplicate item IDs across the requested feeds while preserving their first
   appearance.
5. Fetch each unique item once, persist the raw response, and upsert its
   normalized version.

For example, if an item is present in both `topstories` and `newstories`, both
rank observations are retained, but the item detail endpoint is fetched once
during that run.

## Data model and history

| Table | Purpose |
| --- | --- |
| `raw.hn_feed_responses` | Immutable observations of feed payloads, including their payload hash and fetch time. |
| `raw.hn_item_responses` | Immutable observations of individual Hacker News item payloads. Repeated reads are retained. |
| `staging.feed_rank_snapshots` | One row per item and position in a specific feed response. This preserves ranking history. |
| `staging.item_versions` | One normalized version per `(item_id, payload_hash)`. Re-observing the same payload updates `last_seen_at`; a changed payload creates a new version. |

This means two staging versions for the same story can be correct. For example,
when its `score` changes, its API payload hash changes too, so the project
stores a new historical version instead of overwriting the old one.

## Project structure

```text
.
├── alembic/                         # PostgreSQL schema migrations
├── src/hacker_news_pipeline/
│   ├── api/                         # HN client and Pydantic API schemas
│   ├── db/                          # SQLAlchemy ORM, sessions, repositories
│   ├── pipeline/                    # Hashing and ingestion workflows
│   ├── config.py                    # Environment-based settings
│   ├── logging_config.py
│   └── main.py                      # CLI entry point
├── tests/
│   ├── unit/
│   └── integration/
├── compose.yaml                     # Local PostgreSQL 16 service
└── pyproject.toml
```

## Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Docker and Docker Compose

## Local setup

Create the local configuration file and adjust values if necessary:

```bash
cp .env.example .env
```

The `.env` file is local-only and must not be committed. It contains the
development and test database URLs used by the project.

Start PostgreSQL and install the project dependencies:

```bash
docker compose up -d
uv sync
```

Apply the schema migration to the development database:

```bash
uv run alembic upgrade head
```

The integration suite requires a separate `hacker_news_test` database. Create
it once, then apply the same migrations with the test URL:

```bash
docker compose exec postgres psql \
  -U analytics_user \
  -d postgres \
  -c "CREATE DATABASE hacker_news_test;"

HN_PIPELINE_DATABASE_URL="postgresql+psycopg://analytics_user:change_me_for_local_development@localhost:5433/hacker_news_test" \
  uv run alembic upgrade head
```

If the database already exists, PostgreSQL will report that fact; it is safe to
skip the creation command and run the migration command.

## Run an ingestion

Use one or more `--feed` flags. Each selected feed can contain hundreds of
item IDs, so the command makes one detail request per unique ID.

```bash
uv run python -m hacker_news_pipeline.main --feed topstories

uv run python -m hacker_news_pipeline.main \
  --feed topstories \
  --feed newstories \
  --feed beststories
```

Supported feeds are `newstories`, `topstories`, and `beststories`. The command
returns exit code `0` on success and `1` if the pipeline fails; details are
written through Python logging.

## Verify the stored data

For a quick local inspection:

```bash
docker compose exec postgres psql \
  -U analytics_user \
  -d hacker_news \
  -P pager=off \
  -c 'SELECT COUNT(*) AS raw_feed_responses FROM raw.hn_feed_responses;
      SELECT COUNT(*) AS rank_snapshots FROM staging.feed_rank_snapshots;
      SELECT COUNT(*) AS raw_item_responses FROM raw.hn_item_responses;
      SELECT COUNT(*) AS item_versions FROM staging.item_versions;'
```

## Tests and quality checks

Unit tests isolate API, schema, hashing, CLI, and coordination behavior.
Integration tests use the dedicated PostgreSQL test database and verify ORM
constraints, repositories, transactions, and ingestion persistence.

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
uv run alembic check
```

## Design decisions

- Raw tables preserve every successful API observation for traceability and
  possible reprocessing.
- Payload hashes provide deterministic change detection. JSON object-key order
  does not affect a hash; list order does, because ranking order is meaningful.
- Feed rank snapshots are insert-only and idempotent per raw feed response.
- Item versions use PostgreSQL upsert logic. Repeated identical payloads move
  `last_seen_at` forward without creating a duplicate version.
- Feed and item ingestion each run in their own transaction. The discovery
  workflow coordinates them, while failures are propagated to the CLI instead
  of being silently ignored.

## Current scope and next steps

Implemented:

- Hacker News API client and Pydantic response validation.
- PostgreSQL raw and staging schemas managed by Alembic.
- Raw and staging repositories with database constraints and idempotent writes.
- Feed, item, and discovery ingestion workflows.
- Command-line entry point, structured logging, unit tests, and PostgreSQL
  integration tests.

Planned next:

- dbt intermediate models, marts, documentation, and analytical tests.
- Apache Airflow DAGs for scheduled discovery and changed-item synchronization.
- Support for the `updates` endpoint, users, and more complete comment handling.

## Source

Data is obtained from the [official Hacker News API](https://github.com/HackerNews/API).
