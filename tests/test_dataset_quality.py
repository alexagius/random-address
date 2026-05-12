import json
from pathlib import Path


DATASET_PATH = Path(__file__).resolve().parents[1] / "random_address" / "addresses-us-all.min.json"
OPENADDRESSES_SAMPLE_STATES = {
    "DE", "HI", "IA", "ID", "IL", "IN", "KS", "LA", "ME", "MI",
    "MN", "MO", "MS", "MT", "NC", "ND", "NE", "NJ", "NM", "NV",
    "NY", "OH", "OR", "PA", "RI", "SC", "SD", "TX", "UT", "WA",
    "WI", "WV", "WY",
}


def load_addresses():
    with DATASET_PATH.open("r", encoding="utf-8") as dataset_file:
        return json.load(dataset_file)["addresses"]


def test_openaddresses_sample_records_are_complete():
    addresses = [
        address for address in load_addresses()
        if address.get("state") in OPENADDRESSES_SAMPLE_STATES
    ]

    assert addresses
    for address in addresses:
        coordinates = address.get("coordinates") or {}
        assert address.get("address1")
        assert address.get("city")
        assert address.get("state")
        assert address.get("postalCode")
        assert isinstance(coordinates.get("lat"), (float, int))
        assert isinstance(coordinates.get("lng"), (float, int))


def test_openaddresses_sample_records_include_some_address2_values():
    addresses = [
        address for address in load_addresses()
        if address.get("state") in OPENADDRESSES_SAMPLE_STATES
    ]

    assert sum(1 for address in addresses if address.get("address2")) > 0
