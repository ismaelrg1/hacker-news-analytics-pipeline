# raw.api_responses

raw.hn_item_responses
- raw_item_response_id  -> BIGINT, PK, identity
- source_name           -> VARCHAR(50), Not Null
- item_id               -> BIGINT, Not Null
- response_payload      -> JSONB, Not Null
- payload_hash          -> VARCHAR(64), Not Null
- fetched_at            -> TIMESTAMPTZ, Not Null


payload_hash ~ '^[0-9a-f]{64}$'


raw.hn_feed_responses
- raw_feed_response_id  -> BIGINT, PK, identity
- source_name           -> VARCHAR(50), Not Null
- feed_name             -> VARCHAR(20), Not Null
- response_payload      -> JSONB, Not Null
- payload_hash          -> VARCHAR(64), Not Null
- fetched_at            -> TIMESTAMPTZ, Not Null

payload_hash ~ '^[0-9a-f]{64}$'

feed_name in ('newstories', 'topstories', 'beststories')

# staging.hn_items

staging.hn_item_versions
- hn_item_version_id            -> BIGINT, PK, identity
- item_id                       -> BIGINT, Not Null
- payload_hash                  -> VARCHAR(64), Not Null
- first_raw_response_id         -> BIGINT, FK -> raw.hn_item_responses, Not Null

- first_seen_at                 -> TIMESTAMPTZ, Not Null
- last_seen_at                  -> TIMESTAMPTZ, Not Null
- item_type                     -> VARCHAR(10), NULL
- author_username               -> TEXT, NULL
- created_at                    -> TIMESTAMPTZ, NULL
- is_deleted                    -> BOOL, Not Null, DEFAULT FALSE
- is_dead                       -> BOOL, Not Null, DEFAULT FALSE
- parent_item_id                -> BIGINT, NULL
- title                         -> TEXT, NULL
- text                          -> TEXT, NULL
- url                           -> TEXT, NULL
- score                         -> INTEGER, NULL
- descendants_count             -> INTEGER, NULL

prevalidate( time Unix Time to TimeStamptz)

check item_type IS NULL
OR item_type IN ('job', 'story', 'comment', 'poll', 'pollopt')

score IS NULL OR score >= 0

descendant_count IS NULL OR descendant_count >= 0

last_seen_at >= first_seen_at

UNIQUE (item_id, payload_hash)

payload_hash ~ '^[0-9a-f]{64}$'


# staging.hn_feed_rank_snapshots

staging.hn_feed_rank_snapshots
- hn_feed_rank_snapshot_id      -> BIGINT, PK, identity
- raw_feed_response_id          -> BIGINT, FK -> raw.hn_feed_responses(raw_feed_response_id), Not Null

- feed_name                     -> VARCHAR(20), Not Null
- item_id                       -> BIGINT, Not Null
- rank_position                 -> INTEGER, Not Null
- observed_at                   -> TIMESTAMPTZ, Not Null

rank_position > 0

feed_name in ('newstories', 'topstories', 'beststories')

UNIQUE (raw_feed_response_id, rank_position)

UNIQUE (raw_feed_response_id, item_id)