SELECT
    item_id,
    hn_item_version_id,
    score,
    previous_score,
    score_change,
    descendants_count,
    previous_descendants_count,
    descendants_change

FROM {{ ref('mart_story_engagement_changes') }}

WHERE (
    (previous_score IS NULL OR score IS NULL)
    AND score_change IS NOT NULL
)
OR (
    previous_score IS NOT NULL
    AND score IS NOT NULL
    AND score_change IS DISTINCT FROM score - previous_score
)
OR (
    (previous_descendants_count IS NULL OR descendants_count IS NULL)
    AND descendants_change IS NOT NULL
)
OR (
    previous_descendants_count IS NOT NULL
    AND descendants_count IS NOT NULL
    AND descendants_change IS DISTINCT FROM descendants_count - previous_descendants_count
)