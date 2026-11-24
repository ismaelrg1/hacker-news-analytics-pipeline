WITH ranked_feed_snapshots AS (
    SELECT
        raw_feed_response_id,
        feed_name,
        item_id,
        rank_position,
        observed_at,

        DENSE_RANK() OVER (
            PARTITION BY feed_name
            ORDER BY 
                observed_at DESC,
                raw_feed_response_id DESC
        ) AS snapshot_recency

    FROM {{ source('hacker_news_staging', 'feed_rank_snapshots') }}
)


SELECT
    raw_feed_response_id,
    feed_name,
    item_id,
    rank_position,
    observed_at

FROM ranked_feed_snapshots
WHERE snapshot_recency = 1