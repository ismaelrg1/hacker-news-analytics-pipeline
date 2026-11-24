SELECT
    hn_item_version_id,
    item_id,
    payload_hash,
    first_seen_at,
    last_seen_at,

    score,
    previous_score,
    score - previous_score AS score_change,
    
    descendants_count,
    previous_descendants_count,
    descendants_count - previous_descendants_count AS descendants_change,

    previous_first_seen_at

FROM {{ ref('int_story_version_history') }}