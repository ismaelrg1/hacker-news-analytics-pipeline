SELECT
    item_id

FROM {{ ref('int_story_version_history') }}
WHERE previous_first_seen_at > first_seen_at