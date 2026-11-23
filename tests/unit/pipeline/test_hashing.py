import re

from hacker_news_pipeline.pipeline.hashing import calculate_payload_hash


def test_same_payload_produce_hash() -> None:
    response_payload_1 = [1, 2, 3]
    response_payload_2 = [1, 2, 3]

    hash_1 = calculate_payload_hash(response_payload_1)
    hash_2 = calculate_payload_hash(response_payload_2)

    assert hash_1 == hash_2


def test_list_order_changes_hash() -> None:
    response_payload_1 = [1, 2, 3]
    response_payload_2 = [3, 1, 2]

    assert calculate_payload_hash(response_payload_1) != calculate_payload_hash(
        response_payload_2
    )


def test_changed_list_value_changes_hash() -> None:
    response_payload_1 = [1, 2, 3]
    response_payload_2 = [1, 2, 4]

    hash_1 = calculate_payload_hash(response_payload_1)
    hash_2 = calculate_payload_hash(response_payload_2)

    assert hash_1 != hash_2


def test_dictionary_key_order_does_not_change_hash() -> None:
    response_payload_1 = {"id": 12, "title": "A story"}
    response_payload_2 = {"title": "A story", "id": 12}

    hash_1 = calculate_payload_hash(response_payload_1)
    hash_2 = calculate_payload_hash(response_payload_2)

    assert hash_1 == hash_2


def test_hash_has_valid_sha256_format() -> None:
    response_payload = [1, 2, 3]

    digest = calculate_payload_hash(response_payload)

    assert len(digest) == 64
    assert re.fullmatch(r"[0-9a-f]{64}", digest) is not None
