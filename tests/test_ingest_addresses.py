import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "data" / "ingest_addresses.py"
SPEC = importlib.util.spec_from_file_location("ingest_addresses", SCRIPT_PATH)
ingest_addresses = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ingest_addresses)


def test_normalize_csv_openaddresses_row():
    record = {
        "properties": {
            "NUMBER": "123",
            "STREET": "Main Street",
            "UNIT": "2A",
            "CITY": "Albany",
            "POSTCODE": "12207-1234",
            "LON": "-73.7562",
            "LAT": "42.6526",
        },
        "coordinates": (-73.7562, 42.6526),
    }

    address = ingest_addresses.normalize_record(record, state="NY")

    assert address == {
        "address1": "123 Main Street",
        "address2": "2A",
        "city": "Albany",
        "state": "NY",
        "postalCode": "12207",
        "coordinates": {
            "lat": 42.6526,
            "lng": -73.7562,
        },
    }


def test_merge_dataset_dedupes_and_appends_attribution(tmp_path):
    base = tmp_path / "base.json"
    output = tmp_path / "output.json"
    source = tmp_path / "source.geojson"

    existing = {
        "addresses": [
            {
                "address1": "123 Main Street",
                "address2": "",
                "city": "Albany",
                "state": "NY",
                "postalCode": "12207",
                "coordinates": {"lat": 42.6526, "lng": -73.7562},
            }
        ],
        "attribution": [],
    }
    base.write_text(json.dumps(existing), encoding="utf-8")

    features = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "number": "123",
                    "street": "Main Street",
                    "city": "Albany",
                    "postcode": "12207",
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-73.7562, 42.6526],
                },
            },
            {
                "type": "Feature",
                "properties": {
                    "number": "456",
                    "street": "State Street",
                    "city": "Albany",
                    "postcode": "12207",
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-73.75, 42.65],
                },
            },
        ],
    }
    source.write_text(json.dumps(features), encoding="utf-8")

    args = ingest_addresses.parse_args(
        [
            "--input",
            str(source),
            "--state",
            "NY",
            "--base",
            str(base),
            "--output",
            str(output),
            "--attribution",
            "Example County (NY)",
        ]
    )

    merged = ingest_addresses.merge_dataset(args)

    assert len(merged["addresses"]) == 2
    assert merged["addresses"][1]["address1"] == "456 State Street"
    assert merged["attribution"] == ["Example County (NY)"]


def test_newline_delimited_geojson_source(tmp_path):
    source = tmp_path / "source.geojson"
    features = [
        {
            "type": "Feature",
            "properties": {
                "number": "1",
                "street": "Main Street",
                "city": "Albany",
                "postcode": "12207",
            },
            "geometry": {"type": "Point", "coordinates": [-73.7562, 42.6526]},
        },
        {
            "type": "Feature",
            "properties": {
                "number": "2",
                "street": "State Street",
                "city": "Albany",
                "postcode": "12207",
            },
            "geometry": {"type": "Point", "coordinates": [-73.75, 42.65]},
        },
    ]
    source.write_text("\n".join(json.dumps(feature) for feature in features), encoding="utf-8")

    records = list(ingest_addresses.iter_geojson_records(source))

    assert len(records) == 2
    assert records[1]["properties"]["street"] == "State Street"


def test_per_postal_code_sampling_is_reproducible():
    addresses = [
        {
            "address1": f"{index} Main Street",
            "address2": "",
            "city": "Albany",
            "state": "NY",
            "postalCode": "12207",
            "coordinates": {"lat": 42.0, "lng": -73.0},
        }
        for index in range(10)
    ]

    first = ingest_addresses.sample_addresses(
        addresses, limit=None, per_postal_code=3, seed=42
    )
    second = ingest_addresses.sample_addresses(
        addresses, limit=None, per_postal_code=3, seed=42
    )

    assert first == second
    assert len(first) == 3


def test_normalize_record_can_allow_missing_postal_code():
    record = {
        "properties": {
            "number": "615",
            "street": "Amherst Street",
            "city": "Nashua",
            "postcode": "",
        },
        "coordinates": (-71.4676, 42.7654),
    }

    address = ingest_addresses.normalize_record(
        record,
        state="NH",
        require_postal_code=False,
    )

    assert address["state"] == "NH"
    assert address["postalCode"] == ""
