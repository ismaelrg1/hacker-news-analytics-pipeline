# Analytics Questions

This document describes the analytical datasets currently published by dbt.
The examples assume the local `dev` target, whose schema is `dbt_dev`.

## Important definitions

- **Current item version** means the item payload most recently observed by the
  pipeline. Hacker News does not expose an item-update timestamp, so this is
  not necessarily the exact time at which Hacker News changed the item.
- **Current feed snapshot** means the most recently observed response for each
  ingested discovery feed.
- The pipeline only has data for feeds that have actually been requested with
  the Python CLI.

## Which visible stories do we currently know about?

**Model:** `mart_current_stories`

**Question:** What is the latest known state of every visible Hacker News story
observed by the pipeline?

**Grain:** one row per `item_id`.

**Includes:** story identifier, author, creation time, title, text, URL, score,
comment count, and the first and last times that the selected payload version
was observed.

**Excludes:** jobs, comments, polls, poll options, deleted items, and dead
items.

Example exploration query:

```sql
SELECT
    item_id,
    title,
    author_username,
    score,
    descendants_count,
    created_at
FROM dbt_dev.mart_current_stories
ORDER BY score DESC NULLS LAST, item_id;
```

The output changes as the pipeline observes new payload versions.

## Which stories are currently ranked in each discovery feed?

**Model:** `mart_current_story_rankings`

**Question:** Which visible stories are present in the latest observed snapshot
of each discovery feed, and what is their original Hacker News rank?

**Grain:** one row per `feed_name` and `rank_position`.

**Feeds:** `newstories`, `topstories`, and `beststories`.

**Includes:** the raw response that produced the snapshot, observation time,
feed name, original rank position, and the current story attributes such as
title, author, score, and comment count.

**Important behavior:** rank positions come directly from Hacker News. If a
feed contains a job or another non-story item, that item is excluded from this
story-only mart; consequently, the displayed positions can contain gaps.

Example exploration query:

```sql
SELECT
    feed_name,
    rank_position,
    item_id,
    title,
    score,
    descendants_count,
    observed_at
FROM dbt_dev.mart_current_story_rankings
ORDER BY feed_name, rank_position;
```

The model intentionally keeps the same story more than once when it appears in
different feeds. Those rows represent different ranking observations, not
duplicates.

## How have story score and comment count changed between observed versions?

**Model:** `mart_story_engagement_changes`

**Question:** How did a story's score and total comment count change between a
distinct observed payload version and its preceding observed version?

**Grain:** one row per `item_id` and `payload_hash`.

**Includes:** the current and previous score, the current and previous total
comment count, the absolute changes between them, and the first and last times
that each payload version was observed.

**First version behavior:** the first observed version of a story has no
previous version. Its `previous_*` and change fields are therefore `NULL`; the
model does not assume that the story started from score or comment count zero.

**Important limitation:** these are changes detected between pipeline
observations, not the exact time at which Hacker News changed the story. A new
payload version can also result from a field other than score or comment count
changing, so both engagement changes can legitimately be zero.

Example exploration query:

```sql
SELECT
    item_id,
    first_seen_at,
    score,
    previous_score,
    score_change,
    descendants_count,
    previous_descendants_count,
    descendants_change
FROM dbt_dev.mart_story_engagement_changes
WHERE item_id = 50547698
ORDER BY first_seen_at, hn_item_version_id;
```

## Related dbt models

```text
staging.item_versions
    -> int_current_item_versions
    -> mart_current_stories

staging.item_versions
    -> int_story_version_history
    -> mart_story_engagement_changes

staging.feed_rank_snapshots
    -> int_latest_feed_snapshots

int_latest_feed_snapshots + mart_current_stories
    -> mart_current_story_rankings
```

The dbt tests enforce the main contracts: current item uniqueness, allowed feed
and item types, required fields, uniqueness of `feed_name` plus `rank_position`
for the latest snapshots and story-ranking mart, temporal ordering of story
versions, and consistency of calculated engagement changes.
