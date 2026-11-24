WITH ranked_item_versions AS (

    SELECT
        hn_item_version_id,
        item_id,
        payload_hash,
        item_type,
        author_username,
        created_at,
        is_deleted,
        is_dead,
        parent_item_id,
        title,
        text,
        url,
        score,
        descendants_count,
        first_seen_at,
        last_seen_at,
        -- columnas que quieras exponer,
        ROW_NUMBER() OVER (
            PARTITION BY item_id
            ORDER BY
                last_seen_at DESC,
                hn_item_version_id DESC
        ) AS version_recency

    FROM {{ source('hacker_news_staging', 'item_versions') }}

)

SELECT
    hn_item_version_id,
    item_id,
    payload_hash,
    item_type,
    author_username,
    created_at,
    is_deleted,
    is_dead,
    parent_item_id,
    title,
    text,
    url,
    score,
    descendants_count,
    first_seen_at,
    last_seen_at
    -- las columnas del CTE, sin version_recency
FROM ranked_item_versions
WHERE version_recency = 1