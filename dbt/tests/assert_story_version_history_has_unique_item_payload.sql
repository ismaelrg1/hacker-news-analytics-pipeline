SELECT
    item_id,
    payload_hash

FROM {{ ref('int_story_version_history') }}
GROUP BY
    item_id,
    payload_hash
HAVING COUNT(*) > 1