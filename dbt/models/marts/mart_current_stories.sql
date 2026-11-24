
SELECT
    item_id,
    item_type,
    hn_item_version_id,
    payload_hash,
    author_username,
    created_at,
    title,
    text,
    url,
    score,
    descendants_count,
    first_seen_at,
    last_seen_at

FROM {{ ref('int_current_item_versions')  }}
WHERE item_type = 'story'
    AND is_deleted = FALSE
    AND is_dead = FALSE