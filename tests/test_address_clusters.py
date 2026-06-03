import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "data" / "address_clusters.py"
SPEC = importlib.util.spec_from_file_location("address_clusters", MODULE_PATH)
address_clusters = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(address_clusters)


def address(index, lat, lng):
    return {
        "address1": f"{index} Main Street",
        "address2": "",
        "city": "Albany",
        "state": "NY",
        "postalCode": "12207",
        "coordinates": {"lat": lat, "lng": lng},
    }


def test_build_clusters_keeps_nearby_zip_records():
    addresses = [
        address(1, 42.0000, -73.0000),
        address(2, 42.0001, -73.0001),
        address(3, 42.0002, -73.0002),
        address(4, 43.0000, -74.0000),
        address(5, 43.0100, -74.0100),
        address(6, 43.0200, -74.0200),
    ]

    clusters = address_clusters.build_clusters(
        addresses,
        cluster_size=3,
        min_postal_code_count=3,
    )

    assert len(clusters) == 1
    assert clusters[0]["state"] == "NY"
    assert clusters[0]["postalCode"] == "12207"
    assert clusters[0]["count"] == 3
    assert sorted(clusters[0]["address_indexes"]) == [0, 1, 2]
    assert clusters[0]["radius_km"] < 0.02


def test_attach_clusters_replaces_existing_metadata():
    data = {
        "addresses": [
            address(1, 42.0000, -73.0000),
            address(2, 42.0001, -73.0001),
            address(3, 42.0002, -73.0002),
        ],
        "clusters": [{"id": "stale"}],
    }

    address_clusters.attach_clusters(
        data,
        cluster_size=3,
        min_postal_code_count=3,
    )

    assert len(data["clusters"]) == 1
    assert data["clusters"][0]["id"] != "stale"
