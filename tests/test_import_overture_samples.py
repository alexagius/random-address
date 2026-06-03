import importlib.util
import json
import sys
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SCRIPT_PATH = DATA_DIR / "import_overture_samples.py"
sys.path.insert(0, str(DATA_DIR))
SPEC = importlib.util.spec_from_file_location("import_overture_samples", SCRIPT_PATH)
import_overture_samples = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(import_overture_samples)


def address(index, lat, lng):
    return {
        "address1": f"{index} Main Street",
        "address2": "",
        "city": "Albany",
        "state": "NY",
        "postalCode": "12207",
        "coordinates": {"lat": lat, "lng": lng},
    }


def test_overture_import_defaults_to_clustered_35_per_zip():
    args = import_overture_samples.parse_args(["--states", "NY", "--dry-run"])

    assert args.per_postal_code == 35
    assert args.sample_mode == "clustered"


def test_clustered_overture_query_orders_by_dense_grid_cell():
    args = import_overture_samples.parse_args(["--states", "NY", "--dry-run"])
    query = import_overture_samples.build_query(args)

    assert "ORDER BY grid_count DESC, lat_bucket, lng_bucket, hash(id)" in query
    assert "WHERE sample_rank <= 35" in query


def test_import_samples_can_attach_cluster_metadata(monkeypatch, tmp_path):
    base = tmp_path / "base.json"
    output = tmp_path / "output.json"
    base.write_text(json.dumps({"addresses": [], "attribution": []}), encoding="utf-8")
    incoming = [
        address(1, 42.0000, -73.0000),
        address(2, 42.0001, -73.0001),
        address(3, 42.0002, -73.0002),
    ]
    monkeypatch.setattr(
        import_overture_samples,
        "fetch_overture_addresses",
        lambda args: incoming,
    )
    args = import_overture_samples.parse_args([
        "--states",
        "NY",
        "--base",
        str(base),
        "--output",
        str(output),
        "--replace-dataset",
        "--build-clusters",
        "--cluster-size",
        "3",
        "--min-cluster-postal-code-count",
        "3",
        "--dry-run",
    ])

    data = import_overture_samples.import_samples(args)

    assert len(data["addresses"]) == 3
    assert len(data["clusters"]) == 1
    assert data["clusters"][0]["address_indexes"] == [0, 1, 2]
