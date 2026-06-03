"""Import per-ZIP samples from Overture Maps address data.

This is intended for larger, reproducible refreshes than the small
OpenAddresses job-sample importer. It queries Overture's public GeoParquet
files with DuckDB, keeps complete US address records only, and samples a
deterministic handful of records per state/ZIP pair.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from address_clusters import attach_clusters
from ingest_addresses import (
    DEFAULT_DATASET,
    VALID_STATES,
    Address,
    dedupe_addresses,
    load_dataset,
    summarize,
    write_dataset,
)


DEFAULT_RELEASE = "2026-04-15.0"
DEFAULT_OVERTURE_PATH = (
    "s3://overturemaps-us-west-2/release/{release}/theme=addresses/type=address/*"
)
DEFAULT_ATTRIBUTION = (
    "Overture Maps Foundation addresses theme, release {release}; "
    "includes source-specific terms listed by Overture."
)


def require_duckdb() -> Any:
    try:
        import duckdb
    except ImportError as error:
        raise RuntimeError(
            "DuckDB is required for the Overture importer. Install it in the "
            "project virtual environment with: python -m pip install duckdb"
        ) from error
    return duckdb


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def state_filter(states: Sequence[str]) -> str:
    invalid = sorted(set(states) - VALID_STATES)
    if invalid:
        raise ValueError(f"Unsupported state code(s): {', '.join(invalid)}")
    return ", ".join(sql_string(state) for state in sorted(set(states)))


def overture_path(args: argparse.Namespace) -> str:
    if args.overture_path:
        return args.overture_path
    return DEFAULT_OVERTURE_PATH.format(release=args.release)


def build_query(args: argparse.Namespace) -> str:
    path = overture_path(args)
    states_sql = state_filter(args.states or sorted(VALID_STATES))
    per_postal_code = int(args.per_postal_code)
    cluster_grid_scale = float(args.cluster_grid_scale)
    sample_order = sample_rank_order(args)
    limit_clause = f"\nLIMIT {int(args.limit)}" if args.limit else ""

    return f"""
WITH candidates AS (
    SELECT
        regexp_replace(trim(number || ' ' || street), '\\s+', ' ', 'g') AS address1,
        coalesce(nullif(trim(unit), ''), '') AS address2,
        coalesce(
            nullif(trim(postal_city), ''),
            nullif(trim(address_levels[2].value), '')
        ) AS city,
        trim(address_levels[1].value) AS state,
        regexp_extract(postcode, '^[0-9]{{5}}', 0) AS postalCode,
        ST_Y(geometry) AS lat,
        ST_X(geometry) AS lng,
        id
    FROM read_parquet({sql_string(path)}, hive_partitioning=1)
    WHERE country = 'US'
        AND address_levels[1].value IN ({states_sql})
        AND postcode IS NOT NULL
        AND regexp_matches(postcode, '^[0-9]{{5}}')
        AND regexp_extract(postcode, '^[0-9]{{5}}', 0) NOT IN ('00000', '99999')
        AND number IS NOT NULL
        AND trim(number) <> ''
        AND street IS NOT NULL
        AND trim(street) <> ''
        AND coalesce(
            nullif(trim(postal_city), ''),
            nullif(trim(address_levels[2].value), '')
        ) IS NOT NULL
        AND lower(coalesce(
            nullif(trim(postal_city), ''),
            nullif(trim(address_levels[2].value), '')
        )) <> 'not stated'
        AND geometry IS NOT NULL
), scored AS (
    SELECT
        *,
        floor(lat * {cluster_grid_scale}) AS lat_bucket,
        floor(lng * {cluster_grid_scale}) AS lng_bucket
    FROM candidates
), ranked AS (
    SELECT
        *,
        count(*) OVER (
            PARTITION BY state, postalCode, lat_bucket, lng_bucket
        ) AS grid_count
    FROM scored
), sampled AS (
    SELECT
        address1,
        address2,
        city,
        state,
        postalCode,
        lat,
        lng,
        row_number() OVER (
            PARTITION BY state, postalCode
            ORDER BY {sample_order}
        ) AS sample_rank
    FROM ranked
)
SELECT address1, address2, city, state, postalCode, lat, lng
FROM sampled
WHERE sample_rank <= {per_postal_code}
ORDER BY state, postalCode, city, address1, address2{limit_clause}
""".strip()


def sample_rank_order(args: argparse.Namespace) -> str:
    if args.sample_mode == "clustered":
        return "grid_count DESC, lat_bucket, lng_bucket, hash(id)"
    return "hash(id)"


def rows_to_addresses(rows: Iterable[Sequence[Any]]) -> List[Address]:
    addresses = []
    for address1, address2, city, state, postal_code, lat, lng in rows:
        if not all((address1, city, state, postal_code)):
            continue
        if lat is None or lng is None:
            continue
        addresses.append({
            "address1": address1,
            "address2": address2 or "",
            "city": city,
            "state": state,
            "postalCode": postal_code,
            "coordinates": {
                "lat": float(lat),
                "lng": float(lng),
            },
        })
    return addresses


def fetch_overture_addresses(args: argparse.Namespace) -> List[Address]:
    duckdb = require_duckdb()
    connection = duckdb.connect()
    connection.execute("INSTALL httpfs")
    connection.execute("LOAD httpfs")
    connection.execute("INSTALL spatial")
    connection.execute("LOAD spatial")
    connection.execute("SET s3_region='us-west-2'")
    connection.execute(f"SET http_timeout={int(args.http_timeout)}")
    connection.execute(f"SET http_retries={int(args.http_retries)}")
    connection.execute(f"SET http_retry_wait_ms={int(args.http_retry_wait_ms)}")
    connection.execute("SET enable_http_metadata_cache=true")
    connection.execute("SET httpfs_connection_caching=true")
    rows = connection.execute(build_query(args)).fetchall()
    return rows_to_addresses(rows)


def attribution(args: argparse.Namespace) -> str:
    return args.attribution or DEFAULT_ATTRIBUTION.format(release=args.release)


def import_samples(args: argparse.Namespace) -> Dict[str, Any]:
    data = load_dataset(args.base)
    incoming = fetch_overture_addresses(args)

    if args.replace_dataset:
        existing_addresses: List[Address] = []
    else:
        existing_addresses = data.get("addresses", [])

    incoming = dedupe_addresses(existing_addresses, incoming)
    data["addresses"] = existing_addresses + incoming
    if args.build_clusters:
        attach_clusters(
            data,
            cluster_size=args.cluster_size,
            min_postal_code_count=args.min_cluster_postal_code_count,
        )
    else:
        data.pop("clusters", None)

    attributions = list(data.get("attribution", []))
    source_attribution = attribution(args)
    if source_attribution not in attributions:
        attributions.append(source_attribution)
    data["attribution"] = attributions

    print("Imported:", json.dumps(summarize(incoming), sort_keys=True))
    print("Merged:", json.dumps(summarize(data["addresses"]), sort_keys=True))
    if args.build_clusters:
        print("Clusters:", json.dumps({"clusters": len(data["clusters"])}, sort_keys=True))

    if not args.dry_run:
        write_dataset(args.output, data, pretty=args.pretty)
        print(f"Wrote {args.output}")

    return data


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import complete per-ZIP address samples from Overture Maps."
    )
    parser.add_argument(
        "--states",
        nargs="+",
        choices=sorted(VALID_STATES),
        help="State codes to import. Defaults to all supported US states and DC.",
    )
    parser.add_argument(
        "--per-postal-code",
        type=int,
        default=35,
        help="Maximum Overture addresses to keep per state/ZIP pair.",
    )
    parser.add_argument(
        "--sample-mode",
        choices=("random", "clustered"),
        default="clustered",
        help="Sample records randomly or by densest coordinate grid cell per state/ZIP.",
    )
    parser.add_argument(
        "--cluster-grid-scale",
        type=float,
        default=100.0,
        help="Grid scale for clustered Overture sampling. 100 means 0.01 degree cells.",
    )
    parser.add_argument(
        "--http-timeout",
        type=int,
        default=180,
        help="DuckDB httpfs timeout in seconds for long S3 parquet scans.",
    )
    parser.add_argument(
        "--http-retries",
        type=int,
        default=8,
        help="DuckDB httpfs retry count for transient S3 read failures.",
    )
    parser.add_argument(
        "--http-retry-wait-ms",
        type=int,
        default=500,
        help="Initial DuckDB httpfs retry wait in milliseconds.",
    )
    parser.add_argument(
        "--release",
        default=DEFAULT_RELEASE,
        help="Overture release to query when --overture-path is not set.",
    )
    parser.add_argument(
        "--overture-path",
        help="Override the Overture GeoParquet path. Useful for a pinned local copy.",
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
        help="Maximum incoming addresses after per-ZIP sampling; mainly for tests.",
    )
    parser.add_argument(
        "--replace-dataset",
        action="store_true",
        help="Replace the packaged address list instead of merging into it.",
    )
    parser.add_argument(
        "--build-clusters",
        action="store_true",
        help="Regenerate compact ZIP-level cluster metadata after importing.",
    )
    parser.add_argument(
        "--cluster-size",
        type=int,
        default=35,
        help="Number of nearby addresses to store in each generated ZIP cluster.",
    )
    parser.add_argument(
        "--min-cluster-postal-code-count",
        type=int,
        default=6,
        help="Minimum records required before a ZIP can receive cluster metadata.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Write formatted JSON instead of minified JSON.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the import summary without writing the output file.",
    )
    args = parser.parse_args(argv)
    if args.per_postal_code < 1:
        parser.error("--per-postal-code must be at least 1")
    if args.cluster_grid_scale <= 0:
        parser.error("--cluster-grid-scale must be greater than 0")
    if args.http_timeout < 1:
        parser.error("--http-timeout must be at least 1")
    if args.http_retries < 0:
        parser.error("--http-retries must be non-negative")
    if args.http_retry_wait_ms < 0:
        parser.error("--http-retry-wait-ms must be non-negative")
    if args.cluster_size < 1:
        parser.error("--cluster-size must be at least 1")
    if args.min_cluster_postal_code_count < 1:
        parser.error("--min-cluster-postal-code-count must be at least 1")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    import_samples(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
