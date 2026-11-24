SELECT
    item_id,
    payload_hash

FROM {{ ref('mart_story_engagement_changes') }}
GROUP BY
    item_id,
    payload_hash
HAVING COUNT(*) > 1
