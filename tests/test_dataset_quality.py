import json
from pathlib import Path


DATASET_PATH = Path(__file__).resolve().parents[1] / "random_address" / "addresses-us-all.min.json"


def load_addresses():
    with DATASET_PATH.open("r", encoding="utf-8") as dataset_file:
        return json.load(dataset_file)["addresses"]


def test_packaged_records_are_complete():
    addresses = load_addresses()

    for address in addresses:
        coordinates = address.get("coordinates") or {}
        assert address.get("address1")
        assert address.get("city")
        assert address.get("state")
        assert address.get("postalCode")
        assert address["postalCode"].isdigit()
        assert len(address["postalCode"]) == 5
        assert address["postalCode"] not in {"00000", "99999"}
        assert isinstance(coordinates.get("lat"), (float, int))
        assert isinstance(coordinates.get("lng"), (float, int))


def test_packaged_records_include_address2_values():
    addresses = load_addresses()

    assert sum(1 for address in addresses if address.get("address2")) > 18000


def test_packaged_records_have_broad_zip_coverage():
    postal_counts = {}
    for address in load_addresses():
        postal_code = address["postalCode"]
        postal_counts[postal_code] = postal_counts.get(postal_code, 0) + 1

    assert len(postal_counts) > 26000
    assert sum(1 for count in postal_counts.values() if count >= 5) > 24000
    assert sum(1 for count in postal_counts.values() if count >= 10) > 24000
