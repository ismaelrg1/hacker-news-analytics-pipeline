# DAG Design: `hn_discovery_analytics`

## Status

Design only. The DAG is not implemented yet.

## Objective

Orchestrate the existing Hacker News discovery ingestion and dbt analytical
build as one reliable workflow.

```text
Python ingestion
    -> PostgreSQL raw and staging layers
    -> dbt build
    -> PostgreSQL analytical views
```

## DAG definition

| Property | Value |
| --- | --- |
| DAG ID | `hn_discovery_analytics` |
| Initial schedule | Manual (`schedule=None`) |
| Catchup | Disabled (`catchup=False`) |
| Intended owner | `data-engineering` |
| Data exchange | PostgreSQL, not XCom |

The DAG will remain manual while the local Airflow integration is developed and
debugged. A periodic schedule will be selected only after repeated successful
manual executions.

## Task graph

```text
ingest_discovery_feeds
        |
        v
dbt_build_analytics
```

The default Airflow dependency requires upstream success. Therefore, dbt is not
executed if ingestion fails.

## Task: `ingest_discovery_feeds`

**Responsibility:** execute the existing Python CLI with all discovery feeds in
one invocation:

```text
topstories
newstories
beststories
```

The ingestion remains one task rather than one task per feed because the Python
workflow deduplicates item IDs across feeds while preserving their first-seen
order. Splitting feeds into separate Airflow tasks would make the same item
eligible for multiple detail requests in one DAG run.

**Outputs:**

- Immutable records in `raw.hn_feed_responses` and `raw.hn_item_responses`.
- Feed positions in `staging.feed_rank_snapshots`.
- Normalized item versions in `staging.item_versions`.

**Retry policy:**

| Setting | Value | Effect |
| --- | --- | --- |
| `retries` | `5` | Five retries after the initial attempt; six attempts at most. |
| `retry_delay` | 5 seconds | Initial wait after a failure. |
| `retry_exponential_backoff` | `2.0` | Doubles each retry delay. |
| `max_retry_delay` | 1 minute | Caps the fifth calculated delay at 60 seconds. |

The resulting retry waits are approximately 5, 10, 20, 40, and 60 seconds.
These retries happen within one DAG run. They are distinct from a future DAG
schedule, which creates independent runs.

The existing raw/staging design makes retries safe: repeated observations are
retained in raw, identical item payload versions update `last_seen_at`, and
rank snapshots are idempotent for one raw feed response.

## Task: `dbt_build_analytics`

**Responsibility:** execute `dbt build` after successful ingestion.

The command will build the dbt intermediate models and marts, then run all dbt
data tests. It reads Python-managed data from `staging` and publishes views in
the configured dbt target schema (`dbt_dev` in local development).

**Inputs:**

- `staging.item_versions`
- `staging.feed_rank_snapshots`

**Outputs:**

- Current item and feed-snapshot intermediate views.
- Current stories and current story-ranking marts.
- Historical story engagement-change mart.
- dbt test results recorded in the Airflow task logs.

If this task fails, raw and staging records from the completed ingestion remain
available. Airflow reports dbt separately as failed, allowing the
transformation or quality issue to be diagnosed without losing source data.

## Data exchange and XCom policy

No feed IDs, item payloads, or dbt result sets are passed through XCom.

```text
ingest_discovery_feeds -> PostgreSQL -> dbt_build_analytics
```

PostgreSQL is the durable interface between tasks. XCom may later carry small
metadata such as record counts or a run identifier, but never the API payloads
or ranking lists.

## Future evolution

After the initial DAG is stable, likely additions are:

- A periodic schedule, chosen from observed duration and freshness needs.
- A changed-items synchronization DAG using the Hacker News `updates` endpoint.
- Separate alerting or notification behavior for ingestion and dbt failures.
- Execution timeouts, concurrency limits, and task-level metrics.
- Additional dbt historical marts, including ranking movement analysis.
