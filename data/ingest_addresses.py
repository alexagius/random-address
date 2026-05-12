"""Ingest OpenAddresses-style source files into the packaged dataset.

This script is intentionally dependency-free so it can run in a fresh checkout.
It supports OpenAddresses CSV exports, GeoJSON FeatureCollections, and newline-
delimited GeoJSON Features.
"""

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "random_address" / "addresses-us-all.min.json"
VALID_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
    "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
    "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
    "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI",
    "WY",
}


Address = Dict[str, Any]


def load_dataset(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as source_file:
        data = json.load(source_file)
    data.setdefault("addresses", [])
    data.setdefault("attribution", [])
    return data


def write_dataset(path: Path, data: Dict[str, Any], pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as target_file:
        if pretty:
            json.dump(data, target_file, indent=2)
            target_file.write("\n")
        else:
            json.dump(data, target_file, separators=(",", ":"))


def detect_format(path: Path, requested_format: str) -> str:
    if requested_format != "auto":
        return requested_format
    if path.suffix.lower() == ".csv":
        return "csv"
    return "geojson"


def iter_source_records(path: Path, source_format: str) -> Iterator[Dict[str, Any]]:
    if source_format == "csv":
        yield from iter_csv_records(path)
    elif source_format == "geojson":
        yield from iter_geojson_records(path)
    else:
        raise ValueError(f"Unsupported source format: {source_format}")


def iter_csv_records(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source_file:
        reader = csv.DictReader(source_file)
        for row in reader:
            yield {"properties": row, "coordinates": csv_coordinates(row)}


def csv_coordinates(row: Dict[str, str]) -> Optional[Tuple[float, float]]:
    lon = first_present(row, ("LON", "lon", "LONGITUDE", "longitude", "lng"))
    lat = first_present(row, ("LAT", "lat", "LATITUDE", "latitude"))
    if lon is None or lat is None:
        return None
    return to_float(lon), to_float(lat)


def iter_geojson_records(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as source_file:
        first_line = source_file.readline()
        if not first_line:
            return

        source_file.seek(0)
        try:
            parsed = json.load(source_file)
        except json.JSONDecodeError:
            source_file.seek(0)
            for line in source_file:
                line = line.strip()
                if line:
                    yield geojson_record(json.loads(line))
            return

    if isinstance(parsed, list):
        for feature in parsed:
            yield geojson_record(feature)
        return

    if parsed.get("type") == "FeatureCollection":
        for feature in parsed.get("features", []):
            yield geojson_record(feature)
        return
    if parsed.get("type") == "Feature":
        yield geojson_record(parsed)


def geojson_record(feature: Dict[str, Any]) -> Dict[str, Any]:
    geometry = feature.get("geometry") or {}
    coordinates = geometry.get("coordinates") or []
    lon = coordinates[0] if len(coordinates) > 0 else None
    lat = coordinates[1] if len(coordinates) > 1 else None
    return {
        "properties": feature.get("properties") or {},
        "coordinates": (
            (to_float(lon), to_float(lat))
            if lon is not None and lat is not None
            else None
        ),
    }


def normalize_record(
    record: Dict[str, Any],
    state: str,
    city_fallback: Optional[str] = None,
    require_postal_code: bool = True,
    require_city: bool = True,
) -> Optional[Address]:
    properties = record.get("properties") or {}
    number = clean_value(first_present(properties, ("NUMBER", "number", "addr:housenumber")))
    street = clean_value(first_present(properties, ("STREET", "street", "addr:street")))
    unit = clean_value(first_present(properties, ("UNIT", "unit", "addr:unit")))
    city = clean_value(first_present(properties, ("CITY", "city", "addr:city"))) or city_fallback
    postcode = clean_postal_code(
        first_present(properties, ("POSTCODE", "postcode", "ZIP", "zip", "addr:postcode"))
    )
    coordinates = record.get("coordinates")

    if (
        not street
        or (require_city and not city)
        or (require_postal_code and not postcode)
        or not coordinates
    ):
        return None

    address1 = f"{number} {street}".strip() if number else street
    lon, lat = coordinates
    if lon is None or lat is None:
        return None

    return {
        "address1": address1,
        "address2": unit or "",
        "city": city or "",
        "state": state,
        "postalCode": postcode,
        "coordinates": {
            "lat": lat,
            "lng": lon,
        },
    }


def first_present(values: Dict[str, Any], keys: Sequence[str]) -> Optional[Any]:
    lower_lookup = {key.lower(): value for key, value in values.items()}
    for key in keys:
        if key in values and values[key] not in (None, ""):
            return values[key]
        lower_key = key.lower()
        if lower_key in lower_lookup and lower_lookup[lower_key] not in (None, ""):
            return lower_lookup[lower_key]
    return None


def clean_value(value: Optional[Any]) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def clean_postal_code(value: Optional[Any]) -> str:
    cleaned = clean_value(value)
    if not cleaned:
        return ""
    if "-" in cleaned:
        return cleaned.split("-", 1)[0]
    return cleaned


def to_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def address_key(address: Address) -> Tuple[str, str, str, str, str]:
    return (
        clean_value(address.get("address1")).lower(),
        clean_value(address.get("address2")).lower(),
        clean_value(address.get("city")).lower(),
        clean_value(address.get("state")).upper(),
        clean_value(address.get("postalCode")),
    )


def sample_addresses(
    addresses: Sequence[Address],
    limit: Optional[int],
    per_postal_code: Optional[int],
    seed: int,
) -> List[Address]:
    selected = list(addresses)
    rng = random.Random(seed)

    if per_postal_code is not None:
        by_postal_code: Dict[str, List[Address]] = defaultdict(list)
        for address in selected:
            by_postal_code[address["postalCode"]].append(address)
        selected = []
        for postal_code in sorted(by_postal_code):
            candidates = by_postal_code[postal_code]
            rng.shuffle(candidates)
            selected.extend(candidates[:per_postal_code])

    if limit is not None and len(selected) > limit:
        selected = rng.sample(selected, limit)

    return sorted(
        selected,
        key=lambda address: (
            address["state"],
            address["postalCode"],
            address["city"],
            address["address1"],
            address["address2"],
        ),
    )


def dedupe_addresses(base: Sequence[Address], incoming: Sequence[Address]) -> List[Address]:
    seen = {address_key(address) for address in base}
    deduped = []
    for address in incoming:
        key = address_key(address)
        if key not in seen:
            seen.add(key)
            deduped.append(address)
    return deduped


def load_new_addresses(args: argparse.Namespace) -> List[Address]:
    state = args.state.upper()
    if state not in VALID_STATES:
        raise ValueError(f"Unsupported state code: {state}")

    addresses = []
    for source_path in args.input:
        source_format = detect_format(source_path, args.format)
        for record in iter_source_records(source_path, source_format):
            address = normalize_record(record, state=state, city_fallback=args.city)
            if address is not None:
                addresses.append(address)

    return sample_addresses(
        addresses,
        limit=args.limit,
        per_postal_code=args.per_postal_code,
        seed=args.seed,
    )


def merge_dataset(
    args: argparse.Namespace,
    incoming: Optional[Sequence[Address]] = None,
) -> Dict[str, Any]:
    data = load_dataset(args.base)
    existing_addresses = data["addresses"]
    existing_attribution = data["attribution"]
    incoming = list(incoming) if incoming is not None else load_new_addresses(args)

    if args.replace_state:
        existing_addresses = [
            address
            for address in existing_addresses
            if address.get("state") != args.state.upper()
        ]

    incoming = dedupe_addresses(existing_addresses, incoming)
    data["addresses"] = existing_addresses + incoming

    if args.attribution and args.attribution not in existing_attribution:
        data["attribution"] = existing_attribution + [args.attribution]

    return data


def summarize(addresses: Iterable[Address]) -> Dict[str, Any]:
    address_list = list(addresses)
    states = Counter(address.get("state") for address in address_list)
    postals = Counter(address.get("postalCode") for address in address_list)
    return {
        "addresses": len(address_list),
        "states": dict(sorted(states.items())),
        "postal_codes": len(postals),
    }


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge OpenAddresses-style source data into addresses-us-all.min.json."
    )
    parser.add_argument(
        "--input",
        nargs="+",
        type=Path,
        required=True,
        help="Source CSV, GeoJSON FeatureCollection, or newline-delimited GeoJSON file(s).",
    )
    parser.add_argument(
        "--format",
        choices=("auto", "csv", "geojson"),
        default="auto",
        help="Source format. Defaults to extension-based auto detection.",
    )
    parser.add_argument("--state", required=True, help="Two-letter state code for the source data.")
    parser.add_argument("--city", help="Fallback city when the source does not provide one.")
    parser.add_argument("--attribution", help="Attribution text to append to the dataset.")
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
        "--limit",
        type=int,
        help="Maximum number of incoming addresses after per-ZIP sampling.",
    )
    parser.add_argument(
        "--per-postal-code",
        type=int,
        help="Maximum number of incoming addresses to keep per postal code.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260512,
        help="Random seed used for reproducible sampling.",
    )
    parser.add_argument(
        "--replace-state",
        action="store_true",
        help="Remove existing addresses for this state before adding incoming records.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Write formatted JSON instead of the package's minified JSON.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the merge summary without writing the output file.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    new_addresses = load_new_addresses(args)
    merged = merge_dataset(args, incoming=new_addresses)

    print("Incoming:", json.dumps(summarize(new_addresses), sort_keys=True))
    print("Merged:", json.dumps(summarize(merged["addresses"]), sort_keys=True))

    if not args.dry_run:
        write_dataset(args.output, merged, pretty=args.pretty)
        print(f"Wrote {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
