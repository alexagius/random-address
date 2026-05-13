import importlib.util
import sys
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SCRIPT_PATH = DATA_DIR / "import_openaddresses_samples.py"
sys.path.insert(0, str(DATA_DIR))
SPEC = importlib.util.spec_from_file_location("import_openaddresses_samples", SCRIPT_PATH)
import_openaddresses_samples = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(import_openaddresses_samples)


def test_choose_sources_prefers_statewide_then_largest():
    rows = [
        {"source": "us/ny/small", "size": 10},
        {"source": "us/ny/statewide", "size": 20},
        {"source": "us/ny/large", "size": 100},
    ]

    selected = import_openaddresses_samples.choose_sources(rows, limit=2)

    assert [row["source"] for row in selected] == [
        "us/ny/statewide",
        "us/ny/large",
    ]


def test_records_from_sample_normalizes_features():
    sample = [
        {
            "type": "Feature",
            "properties": {
                "number": "123",
                "street": "Main Street",
                "unit": "",
                "city": "Albany",
                "postcode": "12207",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [-73.7562, 42.6526],
            },
        }
    ]

    addresses = import_openaddresses_samples.records_from_sample(sample, "NY")

    assert addresses == [
        {
            "address1": "123 Main Street",
            "address2": "",
            "city": "Albany",
            "state": "NY",
            "postalCode": "12207",
            "coordinates": {"lat": 42.6526, "lng": -73.7562},
        }
    ]


def test_records_from_sample_skips_incomplete_features():
    sample = [
        {
            "type": "Feature",
            "properties": {
                "number": "615",
                "street": "Amherst Street",
                "city": "Nashua",
                "postcode": "",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [-71.4676, 42.7654],
            },
        }
    ]

    addresses = import_openaddresses_samples.records_from_sample(sample, "NH")

    assert addresses == []


def test_records_from_sample_uses_explicit_city_fallback():
    sample = [
        {
            "type": "Feature",
            "properties": {
                "number": "2034",
                "street": "Hauser Boulevard",
                "city": "",
                "postcode": "59601",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [-112.027, 46.589],
            },
        }
    ]

    addresses = import_openaddresses_samples.records_from_sample(
        sample,
        "MT",
        city_fallback="Helena",
    )

    assert addresses[0]["city"] == "Helena"
