SELECT
    feed_name,
    rank_position,
    COUNT(*) AS occurrence_count

FROM {{ ref('int_latest_feed_snapshots') }}
GROUP BY
    feed_name,
    rank_position
HAVING COUNT(*) > 1