import json
import gzip
from functools import lru_cache
from pathlib import Path


DATASET_PATH = Path(__file__).resolve().parents[1] / "random_address" / "addresses-us-all.min.json.gz"


@lru_cache(maxsize=1)
def load_dataset():
    with gzip.open(DATASET_PATH, "rt", encoding="utf-8") as dataset_file:
        return json.load(dataset_file)


def load_addresses():
    return load_dataset()["addresses"]


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


def test_packaged_records_include_new_hampshire():
    nh_addresses = [
        address for address in load_addresses()
        if address["state"] == "NH"
    ]
    nh_postal_codes = {address["postalCode"] for address in nh_addresses}

    assert len(nh_addresses) > 2000
    assert len(nh_postal_codes) > 200


def test_packaged_records_include_precomputed_clusters():
    data = load_dataset()
    addresses = data["addresses"]
    clusters = data.get("clusters", [])

    assert len(clusters) > 23000
    for cluster in clusters:
        address_indexes = cluster.get("address_indexes", [])
        assert len(address_indexes) == cluster["count"] == 35
        for address_index in address_indexes:
            assert isinstance(address_index, int)
            assert 0 <= address_index < len(addresses)
            address = addresses[address_index]
            assert address["state"] == cluster["state"]
            assert address["postalCode"] == cluster["postalCode"]
