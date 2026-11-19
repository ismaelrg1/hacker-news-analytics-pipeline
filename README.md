# Hacker News Analytics Pipeline

## Objective

Build a local, end-to-end analytics pipeline for public Hacker News data.

The pipeline will ingest stories, comments, users, rankings, and changed items
from the official Hacker News API. It will preserve raw API evidence, publish
normalized PostgreSQL layers, build tested dbt analytical marts, and use Apache
Airflow to orchestrate ingestion and transformation workflows.

The initial project focus is reliable ingestion and analytics-ready data. A
visual dashboard is deliberately out of scope until the marts are stable.

## Architecture

```text
Hacker News API
        |
        v
Python ingestion + Pydantic validation
        |
        v
PostgreSQL raw and staging layers
        |
        v
dbt intermediate models, marts, and tests
        |
        v
Analytics-ready tables and views

Apache Airflow orchestrates schedules, dependencies, retries, and observability.
```

## Data Flow

```text
Hacker News API
    |
    +--> story feeds: newstories, topstories, beststories
    |
    +--> item details: stories and comments
    |
    +--> changed items and profiles
             |
             v
raw.api_ingestions and raw payload versions
             |
             v
staging current stories, comments, users, and rank snapshots
             |
             v
dbt intermediate transformations
             |
             v
dbt marts for engagement, domains, authors, and ranking history
```

## Planned DAGs

```text
hn_discovery_ingestion
  discover story IDs from feeds
      -> fetch item details
      -> persist raw payloads
      -> normalize current items
      -> capture ranking snapshots

hn_changed_items_sync
  discover changed item and profile IDs
      -> fetch changed payloads
      -> persist new raw versions
      -> update current staging records

hn_daily_analytics
  dbt build core models
      -> dbt build marts
      -> dbt test
      -> publish analytics-ready status
```

The DAGs will be introduced incrementally. The project will begin with a
standalone ingestion pipeline and a PostgreSQL schema before adding dbt and
Airflow orchestration.

## Data Layers

| Layer | Responsibility |
| --- | --- |
| `raw` | Traceable API responses and immutable payload versions. |
| `staging` | Typed, normalized, deduplicated current records and ranking snapshots. |
| `intermediate` | Reusable dbt transformations, such as comment-tree and story-history logic. |
| `mart` | Analytics-ready datasets for BI, exploration, and future dashboards. |

## Technology Stack

- Python 3.12 and `uv`
- `httpx` for HTTP access
- Pydantic v2 and `pydantic-settings` for validation and configuration
- PostgreSQL, SQLAlchemy, Psycopg, and Alembic
- dbt with the PostgreSQL adapter
- Apache Airflow and Docker Compose
- pytest for unit and integration tests
- Ruff and Pyright for code quality and static analysis

## Analytics Outputs

Planned marts include:

- Daily story engagement by feed and story type.
- Story score and comment-count history.
- Most shared external domains.
- Author activity and contribution patterns.
- Comment-tree depth and discussion metrics.
- Story score velocity and ranking movement.

## Reliability and Data Quality

- Use `item_id` as the stable identity for Hacker News items.
- Preserve raw payload versions to support traceability and reprocessing.
- Use idempotent loads and explicit conflict handling for retries and backfills.
- Validate external payloads at the ingestion boundary.
- Record ingestion counts, rejected records, payload hashes, and execution context.
- Add dbt schema, grain, and business-rule tests before publishing marts.
- Keep credentials and local runtime configuration outside version control.

## Project Status

Project initialization in progress.

The Hacker News source and high-level architecture have been selected. Database
schema, Python ingestion, dbt models, Airflow DAGs, and automated tests are not
implemented yet.

## Source

Data is obtained from the [official Hacker News API](https://github.com/HackerNews/API).
