SELECT
    feed_name,
    rank_position,
    COUNT(*) AS occurrence_count

FROM {{ ref('mart_current_story_rankings') }}
GROUP BY
    feed_name,
    rank_position
HAVING COUNT(*) > 1