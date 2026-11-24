SELECT
    item_id,
    hn_item_version_id,
    previous_first_seen_at,
    score_change,
    descendants_change

FROM {{ ref('mart_story_engagement_changes') }}

WHERE previous_first_seen_at IS NULL
    AND (
        score_change IS NOT NULL
        OR descendants_change IS NOT NULL
    )