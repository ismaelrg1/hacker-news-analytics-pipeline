WITH source_versions AS (
    SELECT
        hn_item_version_id,
        item_id,
        payload_hash,
        first_seen_at,
        item_type,
        score,
        descendants_count,
        last_seen_at
    
    FROM {{ source('hacker_news_staging', 'item_versions') }}
    WHERE item_type = 'story'
),

version_history AS (
    SELECT
        hn_item_version_id,
        item_id,
        payload_hash,
        first_seen_at,
        score,
        descendants_count,
        last_seen_at,

        -- Previous version values
        LAG(score) OVER (
            PARTITION BY item_id
            ORDER BY first_seen_at ASC, hn_item_version_id ASC
        ) AS previous_score,

        LAG(descendants_count) OVER (
            PARTITION BY item_id
            ORDER BY first_seen_at ASC, hn_item_version_id ASC
        ) AS previous_descendants_count,
        
        LAG(first_seen_at) OVER (
            PARTITION BY item_id
            ORDER BY first_seen_at ASC, hn_item_version_id ASC
        ) AS previous_first_seen_at

    FROM source_versions
)

SELECT
    hn_item_version_id,
    item_id,
    payload_hash,
    first_seen_at,
    score,
    descendants_count,
    last_seen_at,
    previous_score,
    previous_descendants_count,
    previous_first_seen_at

FROM version_history

