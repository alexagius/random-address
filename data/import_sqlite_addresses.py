"""Import samples from a Netsyms-style SQLite address database.

This is optional and intended for local/private experiments with SQLite sources
that expose zipcode, number, street, street2, city, state, country, latitude,
and longitude columns. The committed dataset is generated from open sources
documented in DATA_INGESTION.md.
"""

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from ingest_addresses import (
    DEFAULT_DATASET,
    VALID_STATES,
    Address,
    dedupe_addresses,
    load_dataset,
    summarize,
    write_dataset,
)


def clean(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def clean_zip(value: Any) -> str:
    zipcode = clean(value)
    if len(zipcode) >= 5 and zipcode[:5].isdigit():
        zipcode = zipcode[:5]
    if zipcode in {"00000", "99999"}:
        return ""
    if len(zipcode) == 5 and zipcode.isdigit():
        return zipcode
    return ""


def row_to_address(row: sqlite3.Row) -> Optional[Address]:
    state = clean(row["state"]).upper()
    postal_code = clean_zip(row["zipcode"])
    number = clean(row["number"])
    street = clean(row["street"])
    city = clean(row["city"])
    lat = row["latitude"]
    lng = row["longitude"]

    if state not in VALID_STATES:
        return None
    if not all((postal_code, street, city)):
        return None
    if lat is None or lng is None:
        return None

    return {
        "address1": f"{number} {street}".strip() if number else street,
        "address2": clean(row["street2"]),
        "city": city,
        "state": state,
        "postalCode": postal_code,
        "coordinates": {
            "lat": float(lat),
            "lng": float(lng),
        },
    }


def fetch_sqlite_addresses(args: argparse.Namespace) -> List[Address]:
    states = set(args.states or VALID_STATES)
    state_placeholders = ", ".join("?" for _ in states)
    query = f"""
WITH candidates AS (
    SELECT
        zipcode,
        number,
        street,
        street2,
        city,
        upper(state) AS state,
        latitude,
        longitude,
        row_number() OVER (
            PARTITION BY upper(state), substr(zipcode, 1, 5)
            ORDER BY rowid
        ) AS sample_rank
    FROM addresses
    WHERE country = 'US'
        AND upper(state) IN ({state_placeholders})
        AND zipcode IS NOT NULL
        AND length(zipcode) >= 5
        AND number IS NOT NULL
        AND street IS NOT NULL
        AND city IS NOT NULL
        AND latitude IS NOT NULL
        AND longitude IS NOT NULL
)
SELECT zipcode, number, street, street2, city, state, latitude, longitude
FROM candidates
WHERE sample_rank <= ?
ORDER BY state, zipcode, city, street, number
"""
    if args.limit:
        query += f"\nLIMIT {int(args.limit)}"

    with sqlite3.connect(args.input) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            query,
            [*sorted(states), int(args.per_postal_code)],
        ).fetchall()

    return [
        address for address in (row_to_address(row) for row in rows)
        if address is not None
    ]


def import_samples(args: argparse.Namespace) -> Dict[str, Any]:
    data = load_dataset(args.base)
    incoming = fetch_sqlite_addresses(args)

    existing_addresses = [] if args.replace_dataset else data.get("addresses", [])
    incoming = dedupe_addresses(existing_addresses, incoming)
    data["addresses"] = existing_addresses + incoming

    if args.attribution:
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
        description="Import sampled addresses from a Netsyms-style SQLite file."
    )
    parser.add_argument("--input", type=Path, required=True, help="SQLite database path.")
    parser.add_argument(
        "--states",
        nargs="+",
        choices=sorted(VALID_STATES),
        help="State codes to import. Defaults to all supported US states and DC.",
    )
    parser.add_argument(
        "--per-postal-code",
        type=int,
        default=5,
        help="Maximum addresses to keep per state/ZIP pair.",
    )
    parser.add_argument(
        "--attribution",
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
        "--limit",
        type=int,
        help="Maximum incoming addresses after per-ZIP sampling.",
    )
    parser.add_argument(
        "--replace-dataset",
        action="store_true",
        help="Replace the packaged address list instead of merging into it.",
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
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    import_samples(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
