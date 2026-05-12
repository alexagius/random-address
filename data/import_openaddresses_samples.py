"""Bootstrap missing-state coverage from OpenAddresses public job samples.

The full OpenAddresses GeoJSON files are large. This script gives this package
an intentionally small first pass for missing states by importing public samples
from a few current address sources per state.
"""

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from ingest_addresses import (
    DEFAULT_DATASET,
    VALID_STATES,
    Address,
    dedupe_addresses,
    load_dataset,
    normalize_record,
    summarize,
    write_dataset,
)


OPENADDRESSES_API = "https://batch.openaddresses.io/api"
INCLUDED_US_CODES = VALID_STATES
REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_ALLOW_MISSING_POSTAL_STATES = {"NH"}


def fetch_json(url: str) -> Any:
    with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.load(response)


def data_url(state: str) -> str:
    query = urllib.parse.urlencode({
        "source": f"us/{state.lower()}",
        "layer": "addresses",
    })
    return f"{OPENADDRESSES_API}/data?{query}"


def job_sample_url(job: int) -> str:
    return f"{OPENADDRESSES_API}/job/{job}/output/sample"


def source_state(source: str) -> Optional[str]:
    parts = source.split("/")
    if len(parts) < 3 or parts[0] != "us":
        return None
    state = parts[1].upper()
    return state if state in VALID_STATES else None


def current_states(data: Dict[str, Any]) -> List[str]:
    return sorted({
        address.get("state")
        for address in data.get("addresses", [])
        if address.get("state")
    })


def missing_states(data: Dict[str, Any]) -> List[str]:
    current = set(current_states(data))
    return sorted(state for state in INCLUDED_US_CODES if state not in current)


def usable_sources(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        row for row in rows
        if row.get("layer") == "addresses"
        and row.get("output", {}).get("output")
        and row.get("job")
        and row.get("size", 0) > 0
        and source_state(row.get("source", ""))
    ]


def choose_sources(rows: Sequence[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    """Choose a compact but useful set of sources for one state."""
    sorted_rows = sorted(rows, key=lambda row: row.get("size", 0), reverse=True)
    statewide = [
        row for row in sorted_rows
        if row.get("source", "").endswith("/statewide")
    ]
    selected: List[Dict[str, Any]] = []

    if statewide:
        selected.append(statewide[0])

    for row in sorted_rows:
        if len(selected) >= limit:
            break
        if row not in selected:
            selected.append(row)

    return selected


def records_from_sample(
    sample: Iterable[Dict[str, Any]],
    state: str,
    allow_missing_postal: bool = False,
) -> List[Address]:
    addresses = []
    for feature in sample:
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        if len(coordinates) < 2:
            continue
        record = {
            "properties": feature.get("properties") or {},
            "coordinates": (coordinates[0], coordinates[1]),
        }
        address = normalize_record(
            record,
            state=state,
            require_postal_code=not allow_missing_postal,
        )
        if address is not None:
            addresses.append(address)
    return addresses


def attribution_for_source(source: Dict[str, Any], state: str) -> str:
    return f"OpenAddresses {source['source']} ({state})"


def import_samples(args: argparse.Namespace) -> Dict[str, Any]:
    data = load_dataset(args.base)
    states = args.states or missing_states(data)
    all_sources = usable_sources(fetch_json(f"{OPENADDRESSES_API}/data"))
    incoming: List[Address] = []
    attributions = list(data.get("attribution", []))
    source_count = 0

    for state in states:
        rows = [
            source for source in all_sources
            if source_state(source.get("source", "")) == state
        ]
        candidates = choose_sources(rows, len(rows))
        if not candidates:
            print(f"{state}: no usable OpenAddresses sources")
            continue

        selected_count = 0
        for source in candidates:
            if selected_count >= args.sources_per_state:
                break

            sample = fetch_json(job_sample_url(source["job"]))
            addresses = records_from_sample(
                sample,
                state,
                allow_missing_postal=state in args.allow_missing_postal_states,
            )
            if not addresses:
                print(f"{state}: {source['source']} job={source['job']} skipped empty sample")
                continue

            incoming.extend(addresses)
            attribution = attribution_for_source(source, state)
            if attribution not in attributions:
                attributions.append(attribution)
            source_count += 1
            selected_count += 1
            print(f"{state}: {source['source']} job={source['job']} addresses={len(addresses)}")

        if selected_count == 0:
            print(f"{state}: no sampled addresses from usable OpenAddresses sources")

    incoming = dedupe_addresses(data.get("addresses", []), incoming)
    data["addresses"] = data.get("addresses", []) + incoming
    data["attribution"] = attributions

    print("Imported:", json.dumps(summarize(incoming), sort_keys=True))
    print("Merged:", json.dumps(summarize(data["addresses"]), sort_keys=True))
    print(f"Sources: {source_count}")

    if not args.dry_run:
        write_dataset(args.output, data, pretty=args.pretty)
        print(f"Wrote {args.output}")

    return data


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import public OpenAddresses job samples for missing US states."
    )
    parser.add_argument(
        "--states",
        nargs="+",
        choices=sorted(VALID_STATES),
        help="State codes to import. Defaults to states missing from the dataset.",
    )
    parser.add_argument(
        "--sources-per-state",
        type=int,
        default=3,
        help="Maximum OpenAddresses sources to sample for each state.",
    )
    parser.add_argument(
        "--allow-missing-postal-states",
        nargs="+",
        choices=sorted(VALID_STATES),
        default=sorted(DEFAULT_ALLOW_MISSING_POSTAL_STATES),
        help=(
            "State codes allowed to import sampled addresses with blank postalCode. "
            "Defaults to NH because current OpenAddresses NH sources omit postcodes."
        ),
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
    import_samples(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
