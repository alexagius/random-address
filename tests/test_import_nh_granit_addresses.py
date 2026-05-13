import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "data" / "import_nh_granit_addresses.py"
sys.path.append(str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("import_nh_granit_addresses", MODULE_PATH)
nh_importer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(nh_importer)


def test_address_from_location_normalizes_complete_geocoder_result():
    location = {
        "location": {"x": -71.460399996239, "y": 42.849710645553},
        "attributes": {
            "Score": 100,
            "StAddr": "9 DUCK POND CIRCLE",
            "City": "LITCHFIELD",
            "Region": "NH",
            "Postal": "03052",
        },
    }

    assert nh_importer.address_from_location(location) == {
        "address1": "9 DUCK POND CIRCLE",
        "address2": "",
        "city": "LITCHFIELD",
        "state": "NH",
        "postalCode": "03052",
        "coordinates": {
            "lat": 42.849710645553,
            "lng": -71.460399996239,
        },
    }


def test_address_from_location_rejects_low_quality_result():
    location = {
        "location": {"x": -71.460399996239, "y": 42.849710645553},
        "attributes": {
            "Score": 75,
            "StAddr": "9 DUCK POND CIRCLE",
            "City": "LITCHFIELD",
            "Region": "NH",
            "Postal": "03052",
        },
    }

    assert nh_importer.address_from_location(location) is None


def test_single_line_address_includes_town_and_state():
    assert nh_importer.single_line_address({
        "StreetAddress": "9 DUCK POND CIRCLE",
        "Town": "Litchfield",
    }) == "9 DUCK POND CIRCLE Litchfield NH"
