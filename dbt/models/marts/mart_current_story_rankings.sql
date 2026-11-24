SELECT
    f.raw_feed_response_id,
    f.feed_name,
    f.rank_position,
    f.observed_at,
    f.item_id,
    m.item_type,
    m.title,
    m.author_username,
    m.url,
    m.score,
    m.descendants_count,
    m.created_at

FROM {{ ref('int_latest_feed_snapshots') }} f
INNER JOIN {{ ref('mart_current_stories') }} m
    ON f.item_id = m.item_id