"""Import New Hampshire addresses from NH GRANIT services.

NH GRANIT's parcel point layer includes street address, town, and coordinates
but not ZIP codes. The companion NH GRANIT geocoder returns ZIP codes for those
same addresses. This importer combines both services and keeps a deterministic
sample of complete, geocoded NH records.
"""

import argparse
import json
import random
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence

from ingest_addresses import (
    DEFAULT_DATASET,
    Address,
    address_key,
    clean_postal_code,
    clean_value,
    load_dataset,
    summarize,
    write_dataset,
)


PARCEL_POINTS_URL = (
    "https://nhgeodata.unh.edu/nhgeodata/rest/services/"
    "CAD/ParcelMosaic/MapServer/0/query"
)
GEOCODER_URL = (
    "https://nhgeodata.unh.edu/nhgeodata/rest/services/"
    "Topical/GC_composite_locator_granit/GeocodeServer/geocodeAddresses"
)
DEFAULT_ATTRIBUTION = (
    "NH GRANIT Parcel Mosaic and GC composite locator (NH); "
    "parcel point source NHDRA/Axiomatic, Inc."
)
REQUEST_TIMEOUT_SECONDS = 60


def chunks(values: Sequence[Any], size: int) -> Iterator[Sequence[Any]]:
    for index in range(0, len(values), size):
        yield values[index:index + size]


def post_json(url: str, params: Dict[str, str]) -> Dict[str, Any]:
    body = urllib.parse.urlencode(params).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.load(response)


def get_json(url: str, params: Dict[str, str]) -> Dict[str, Any]:
    query = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{url}?{query}", timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.load(response)


def fetch_object_ids() -> List[int]:
    response = get_json(PARCEL_POINTS_URL, {
        "f": "json",
        "where": "StreetAddress IS NOT NULL",
        "returnIdsOnly": "true",
    })
    if "error" in response:
        raise RuntimeError(f"NH GRANIT object-id query failed: {response['error']}")
    return sorted(int(object_id) for object_id in response.get("objectIds", []))


def fetch_parcel_features(object_ids: Sequence[int]) -> List[Dict[str, Any]]:
    response = post_json(PARCEL_POINTS_URL, {
        "f": "json",
        "objectIds": ",".join(str(object_id) for object_id in object_ids),
        "outFields": "OBJECTID,Town,StreetAddress",
        "returnGeometry": "true",
        "outSR": "4326",
    })
    if "error" in response:
        raise RuntimeError(f"NH GRANIT parcel query failed: {response['error']}")
    return response.get("features", [])


def geocode_features(features: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    records = []
    for feature in features:
        attributes = feature.get("attributes") or {}
        object_id = attributes.get("OBJECTID")
        single_line = single_line_address(attributes)
        if object_id is None or not single_line:
            continue
        records.append({
            "attributes": {
                "OBJECTID": object_id,
                "SingleLine": single_line,
            },
        })

    if not records:
        return []

    response = post_json(GEOCODER_URL, {
        "f": "json",
        "addresses": json.dumps({"records": records}, separators=(",", ":")),
        "outFields": "*",
        "outSR": "4326",
    })
    if "error" in response:
        raise RuntimeError(f"NH GRANIT geocode query failed: {response['error']}")
    return response.get("locations", [])


def single_line_address(attributes: Dict[str, Any]) -> str:
    street = clean_value(attributes.get("StreetAddress"))
    town = clean_value(attributes.get("Town"))
    if not street or not town:
        return ""
    return f"{street} {town} NH"


def unit_line(attributes: Dict[str, Any]) -> str:
    subaddr = clean_value(attributes.get("SubAddr"))
    if subaddr:
        return subaddr

    unit_type = clean_value(attributes.get("UnitType"))
    unit_name = clean_value(attributes.get("UnitName"))
    if unit_type and unit_name:
        return f"{unit_type} {unit_name}"
    return unit_name


def address_from_location(location: Dict[str, Any]) -> Optional[Address]:
    attributes = location.get("attributes") or {}
    coordinates = location.get("location") or {}
    postal_code = clean_postal_code(attributes.get("Postal"))
    address1 = clean_value(attributes.get("StAddr") or attributes.get("ShortLabel"))
    city = clean_value(attributes.get("City"))
    state = clean_value(attributes.get("Region")).upper()
    score = attributes.get("Score") or 0
    lat = coordinates.get("y")
    lng = coordinates.get("x")

    if state != "NH" or score < 90:
        return None
    if not address1 or not city or not postal_code:
        return None
    if lat is None or lng is None:
        return None

    return {
        "address1": address1,
        "address2": unit_line(attributes),
        "city": city,
        "state": "NH",
        "postalCode": postal_code,
        "coordinates": {
            "lat": float(lat),
            "lng": float(lng),
        },
    }


def sample_object_ids(
    object_ids: Sequence[int],
    seed: int,
    max_candidates: int,
) -> List[int]:
    selected = list(object_ids)
    random.Random(seed).shuffle(selected)
    return selected[:max_candidates]


def fetch_nh_addresses(args: argparse.Namespace) -> List[Address]:
    object_ids = sample_object_ids(
        fetch_object_ids(),
        seed=args.seed,
        max_candidates=args.max_candidates,
    )
    by_postal_code: Counter[str] = Counter()
    addresses: List[Address] = []
    seen = set()

    for object_id_batch in chunks(object_ids, args.query_batch_size):
        features = fetch_parcel_features(object_id_batch)
        for feature_batch in chunks(features, args.geocode_batch_size):
            locations = geocode_features(feature_batch)
            for location in locations:
                address = address_from_location(location)
                if address is None:
                    continue
                postal_code = address["postalCode"]
                if by_postal_code[postal_code] >= args.per_postal_code:
                    continue
                key = address_key(address)
                if key in seen:
                    continue
                seen.add(key)
                addresses.append(address)
                by_postal_code[postal_code] += 1

        if args.pause_seconds:
            time.sleep(args.pause_seconds)

    return sorted(
        addresses,
        key=lambda address: (
            address["postalCode"],
            address["city"],
            address["address1"],
            address["address2"],
        ),
    )


def import_addresses(args: argparse.Namespace) -> Dict[str, Any]:
    data = load_dataset(args.base)
    existing_addresses = [
        address for address in data.get("addresses", [])
        if not args.replace_state or address.get("state") != "NH"
    ]
    incoming = fetch_nh_addresses(args)
    existing_keys = {address_key(address) for address in existing_addresses}
    incoming = [
        address for address in incoming
        if address_key(address) not in existing_keys
    ]

    data["addresses"] = existing_addresses + incoming
    attributions = list(data.get("attribution", []))
    if args.attribution not in attributions:
        attributions.append(args.attribution)
    data["attribution"] = attributions

    print("Imported:", json.dumps(summarize(incoming), sort_keys=True))
    print("Merged:", json.dumps(summarize(data["addresses"]), sort_keys=True))

    if not args.dry_run:
        write_dataset(args.output, data, pretty=args.pretty)
        print(f"Wrote {args.output}")

    return data


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import complete New Hampshire address samples from NH GRANIT."
    )
    parser.add_argument(
        "--per-postal-code",
        type=int,
        default=10,
        help="Maximum NH addresses to keep per ZIP code.",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=50000,
        help="Maximum random parcel points to geocode before sampling.",
    )
    parser.add_argument(
        "--query-batch-size",
        type=int,
        default=500,
        help="Parcel point object IDs to fetch per request.",
    )
    parser.add_argument(
        "--geocode-batch-size",
        type=int,
        default=100,
        help="Addresses to send to the geocoder per request.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260513,
        help="Random seed used for reproducible source sampling.",
    )
    parser.add_argument(
        "--attribution",
        default=DEFAULT_ATTRIBUTION,
        help="Attribution text to append to the dataset.",
    )
    parser.add_argument(
        "--base",
        type=Path,
        default=DEFAULT_DATASET,
        help=f"Existing dataset to merge into. Defaults to {DEFAULT_DATASET}.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_DATASET,
        help=f"Output dataset path. Defaults to {DEFAULT_DATASET}.",
    )
    parser.add_argument(
        "--replace-state",
        action="store_true",
        help="Remove existing NH records before adding incoming records.",
    )
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=0.0,
        help="Optional pause between parcel query batches.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Write formatted JSON instead of the package's minified JSON.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the import summary without writing the output file.",
    )
    args = parser.parse_args(argv)
    if args.per_postal_code < 1:
        parser.error("--per-postal-code must be at least 1")
    if args.max_candidates < 1:
        parser.error("--max-candidates must be at least 1")
    if args.query_batch_size < 1:
        parser.error("--query-batch-size must be at least 1")
    if args.geocode_batch_size < 1:
        parser.error("--geocode-batch-size must be at least 1")
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    import_addresses(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
