"""Build the packaged SQLite address dataset from generated JSON data."""

import argparse
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

from ingest_addresses import ROOT, load_dataset


DEFAULT_INPUT = ROOT / "data" / "work" / "addresses-us-all.min.json.gz"
READABLE_INPUT = ROOT / "addresses-us-all.json"
DEFAULT_OUTPUT = ROOT / "random_address" / "addresses-us-all.sqlite"
SCALE = 10_000_000


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build random_address/addresses-us-all.sqlite from generated address JSON."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=default_input_path(),
        help="Source .json or .json.gz dataset. Defaults to data/work, then addresses-us-all.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"SQLite output path. Defaults to {DEFAULT_OUTPUT}.",
    )
    args = parser.parse_args(argv)
    if not args.input.exists():
        parser.error(f"input dataset not found: {args.input}")
    return args


def default_input_path() -> Path:
    if DEFAULT_INPUT.exists():
        return DEFAULT_INPUT
    return READABLE_INPUT


def build_sqlite_dataset(input_path: Path, output_path: Path) -> None:
    data = load_dataset(input_path)
    addresses = sorted(
        enumerate(data.get("addresses", [])),
        key=address_sort_key,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    state_counts = Counter(address["state"] for _, address in addresses)
    postal_counts = Counter(address["postalCode"] for _, address in addresses)
    city_counts = Counter(address.get("city") for _, address in addresses if address.get("city"))
    state_ids = {state: index + 1 for index, state in enumerate(sorted(state_counts))}
    postal_code_ids = {
        postal_code: index + 1
        for index, postal_code in enumerate(sorted(postal_counts))
    }
    city_ids = {city: index + 1 for index, city in enumerate(sorted(city_counts))}

    original_to_sqlite_id = {
        original_index: sqlite_id
        for sqlite_id, (original_index, _) in enumerate(addresses)
    }

    connection = sqlite3.connect(output_path)
    try:
        initialize_database(connection)
        insert_metadata(
            connection,
            addresses=addresses,
            state_counts=state_counts,
            postal_counts=postal_counts,
            city_counts=city_counts,
            state_ids=state_ids,
            postal_code_ids=postal_code_ids,
            city_ids=city_ids,
            attributions=data.get("attribution", []),
        )
        insert_addresses(
            connection,
            addresses=addresses,
            state_ids=state_ids,
            postal_code_ids=postal_code_ids,
            city_ids=city_ids,
        )
        insert_clusters(
            connection,
            clusters=data.get("clusters", []),
            original_to_sqlite_id=original_to_sqlite_id,
            state_ids=state_ids,
            postal_code_ids=postal_code_ids,
        )
        create_indexes(connection)
        connection.execute("VACUUM")
    finally:
        connection.close()


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        PRAGMA temp_store=MEMORY;
        PRAGMA page_size=4096;

        CREATE TABLE metadata(
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        ) WITHOUT ROWID;

        CREATE TABLE states(
            id INTEGER PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            count INTEGER NOT NULL
        );

        CREATE TABLE postal_codes(
            id INTEGER PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            count INTEGER NOT NULL
        );

        CREATE TABLE cities(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            clean_name TEXT NOT NULL,
            count INTEGER NOT NULL
        );

        CREATE TABLE addresses(
            id INTEGER PRIMARY KEY,
            address1 TEXT NOT NULL,
            address2 TEXT NOT NULL,
            city_id INTEGER NOT NULL,
            state_id INTEGER NOT NULL,
            postal_code_id INTEGER NOT NULL,
            lat_e7 INTEGER NOT NULL,
            lng_e7 INTEGER NOT NULL
        );

        CREATE TABLE state_ranges(
            state_id INTEGER PRIMARY KEY,
            start_id INTEGER NOT NULL,
            end_id INTEGER NOT NULL,
            count INTEGER NOT NULL
        ) WITHOUT ROWID;

        CREATE TABLE state_postal_ranges(
            state_id INTEGER NOT NULL,
            postal_code_id INTEGER NOT NULL,
            start_id INTEGER NOT NULL,
            end_id INTEGER NOT NULL,
            count INTEGER NOT NULL,
            PRIMARY KEY(state_id, postal_code_id)
        ) WITHOUT ROWID;

        CREATE TABLE state_postal_city_ranges(
            state_id INTEGER NOT NULL,
            postal_code_id INTEGER NOT NULL,
            city_id INTEGER NOT NULL,
            start_id INTEGER NOT NULL,
            end_id INTEGER NOT NULL,
            count INTEGER NOT NULL,
            PRIMARY KEY(state_id, postal_code_id, city_id)
        ) WITHOUT ROWID;

        CREATE TABLE clusters(
            id INTEGER PRIMARY KEY,
            cluster_key TEXT NOT NULL UNIQUE,
            state_id INTEGER NOT NULL,
            postal_code_id INTEGER NOT NULL,
            center_lat_e7 INTEGER NOT NULL,
            center_lng_e7 INTEGER NOT NULL,
            radius_m INTEGER NOT NULL,
            count INTEGER NOT NULL
        );

        CREATE TABLE cluster_addresses(
            cluster_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            address_id INTEGER NOT NULL,
            PRIMARY KEY(cluster_id, position)
        ) WITHOUT ROWID;

        CREATE TABLE attribution(
            value TEXT NOT NULL PRIMARY KEY
        ) WITHOUT ROWID;
        """
    )


def insert_metadata(
    connection: sqlite3.Connection,
    addresses: Sequence[Tuple[int, Dict[str, Any]]],
    state_counts: Counter,
    postal_counts: Counter,
    city_counts: Counter,
    state_ids: Dict[str, int],
    postal_code_ids: Dict[str, int],
    city_ids: Dict[str, int],
    attributions: Iterable[str],
) -> None:
    connection.executemany(
        "INSERT INTO metadata(key, value) VALUES (?, ?)",
        [
            ("total_addresses", str(len(addresses))),
            ("unique_states", str(len(state_ids))),
            ("unique_postal_codes", str(len(postal_code_ids))),
            ("unique_cities", str(len(city_ids))),
        ],
    )
    connection.executemany(
        "INSERT INTO states(id, code, count) VALUES (?, ?, ?)",
        [(state_ids[state], state, state_counts[state]) for state in sorted(state_counts)],
    )
    connection.executemany(
        "INSERT INTO postal_codes(id, code, count) VALUES (?, ?, ?)",
        [
            (postal_code_ids[postal_code], postal_code, postal_counts[postal_code])
            for postal_code in sorted(postal_counts)
        ],
    )
    connection.executemany(
        "INSERT INTO cities(id, name, clean_name, count) VALUES (?, ?, ?, ?)",
        [
            (city_ids[city], city, clean_text(city), city_counts[city])
            for city in sorted(city_counts)
        ],
    )
    connection.executemany(
        "INSERT OR IGNORE INTO attribution(value) VALUES (?)",
        [(attribution,) for attribution in attributions],
    )
    connection.commit()


def insert_addresses(
    connection: sqlite3.Connection,
    addresses: Sequence[Tuple[int, Dict[str, Any]]],
    state_ids: Dict[str, int],
    postal_code_ids: Dict[str, int],
    city_ids: Dict[str, int],
) -> None:
    state_ranges: Dict[int, list] = {}
    state_postal_ranges: Dict[Tuple[int, int], list] = {}
    state_postal_city_ranges: Dict[Tuple[int, int, int], list] = {}
    batch = []

    for sqlite_id, (_, address) in enumerate(addresses):
        state_id = state_ids[address["state"]]
        postal_code_id = postal_code_ids[address["postalCode"]]
        city_id = city_ids[address["city"]]
        coordinates = address["coordinates"]
        batch.append((
            sqlite_id,
            address.get("address1") or "",
            address.get("address2") or "",
            city_id,
            state_id,
            postal_code_id,
            scaled_coordinate(coordinates["lat"]),
            scaled_coordinate(coordinates["lng"]),
        ))
        update_range(state_ranges, state_id, sqlite_id)
        update_range(state_postal_ranges, (state_id, postal_code_id), sqlite_id)
        update_range(
            state_postal_city_ranges,
            (state_id, postal_code_id, city_id),
            sqlite_id,
        )
        if len(batch) >= 10_000:
            connection.executemany("INSERT INTO addresses VALUES (?, ?, ?, ?, ?, ?, ?, ?)", batch)
            batch.clear()

    if batch:
        connection.executemany("INSERT INTO addresses VALUES (?, ?, ?, ?, ?, ?, ?, ?)", batch)

    connection.executemany(
        "INSERT INTO state_ranges VALUES (?, ?, ?, ?)",
        [(key, value[0], value[1], value[2]) for key, value in state_ranges.items()],
    )
    connection.executemany(
        "INSERT INTO state_postal_ranges VALUES (?, ?, ?, ?, ?)",
        [
            (key[0], key[1], value[0], value[1], value[2])
            for key, value in state_postal_ranges.items()
        ],
    )
    connection.executemany(
        "INSERT INTO state_postal_city_ranges VALUES (?, ?, ?, ?, ?, ?)",
        [
            (key[0], key[1], key[2], value[0], value[1], value[2])
            for key, value in state_postal_city_ranges.items()
        ],
    )
    connection.commit()


def insert_clusters(
    connection: sqlite3.Connection,
    clusters: Sequence[Dict[str, Any]],
    original_to_sqlite_id: Dict[int, int],
    state_ids: Dict[str, int],
    postal_code_ids: Dict[str, int],
) -> None:
    cluster_rows = []
    cluster_address_rows = []
    for cluster_id, cluster in enumerate(clusters, start=1):
        center = cluster.get("center") or {}
        cluster_rows.append((
            cluster_id,
            cluster.get("id") or f"{cluster.get('state')}-{cluster.get('postalCode')}-{cluster_id}",
            state_ids[cluster["state"]],
            postal_code_ids[cluster["postalCode"]],
            scaled_coordinate(center.get("lat", 0.0)),
            scaled_coordinate(center.get("lng", 0.0)),
            round(float(cluster.get("radius_km", 0.0)) * 1000),
            int(cluster.get("count") or len(cluster.get("address_indexes", []))),
        ))
        for position, original_address_index in enumerate(cluster.get("address_indexes", [])):
            cluster_address_rows.append((
                cluster_id,
                position,
                original_to_sqlite_id[int(original_address_index)],
            ))
            if len(cluster_address_rows) >= 10_000:
                connection.executemany(
                    "INSERT INTO cluster_addresses VALUES (?, ?, ?)",
                    cluster_address_rows,
                )
                cluster_address_rows.clear()

    connection.executemany("INSERT INTO clusters VALUES (?, ?, ?, ?, ?, ?, ?, ?)", cluster_rows)
    if cluster_address_rows:
        connection.executemany(
            "INSERT INTO cluster_addresses VALUES (?, ?, ?)",
            cluster_address_rows,
        )
    connection.commit()


def create_indexes(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE INDEX idx_cities_clean_name ON cities(clean_name, id);
        CREATE INDEX idx_addresses_city_id ON addresses(city_id, id);
        CREATE INDEX idx_clusters_state_postal ON clusters(state_id, postal_code_id, id);
        CREATE INDEX idx_clusters_postal ON clusters(postal_code_id, id);
        """
    )
    connection.commit()


def update_range(ranges: Dict[Any, list], key: Any, address_id: int) -> None:
    if key not in ranges:
        ranges[key] = [address_id, address_id, 0]
    ranges[key][1] = address_id
    ranges[key][2] += 1


def address_sort_key(item: Tuple[int, Dict[str, Any]]) -> Tuple[str, str, str, str, str, int]:
    original_index, address = item
    return (
        address.get("state") or "",
        address.get("postalCode") or "",
        clean_text(address.get("city")),
        clean_text(address.get("address1")),
        clean_text(address.get("address2")),
        original_index,
    )


def scaled_coordinate(value: Any) -> int:
    return round(float(value) * SCALE)


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    build_sqlite_dataset(args.input, args.output)
    print(f"Wrote {args.output} ({args.output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
