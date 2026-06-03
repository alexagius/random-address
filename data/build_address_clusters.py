"""Regenerate build-time cluster metadata for the working JSON dataset."""

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from address_clusters import attach_clusters
from ingest_addresses import DEFAULT_DATASET, load_dataset, write_dataset


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build compact ZIP-level cluster metadata for the address dataset."
    )
    parser.add_argument(
        "--base",
        type=Path,
        default=DEFAULT_DATASET,
        help=f"Dataset to read. Defaults to {DEFAULT_DATASET}.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_DATASET,
        help=f"Dataset to write. Defaults to {DEFAULT_DATASET}.",
    )
    parser.add_argument(
        "--cluster-size",
        type=int,
        default=35,
        help="Number of nearby addresses to store per ZIP cluster.",
    )
    parser.add_argument(
        "--min-postal-code-count",
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
        help="Print the generated cluster count without writing the dataset.",
    )
    args = parser.parse_args(argv)
    if args.cluster_size < 1:
        parser.error("--cluster-size must be at least 1")
    if args.min_postal_code_count < 1:
        parser.error("--min-postal-code-count must be at least 1")
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    data = load_dataset(args.base)
    attach_clusters(
        data,
        cluster_size=args.cluster_size,
        min_postal_code_count=args.min_postal_code_count,
    )
    print("Clusters:", json.dumps({"clusters": len(data["clusters"])}, sort_keys=True))

    if not args.dry_run:
        write_dataset(args.output, data, pretty=args.pretty)
        print(f"Wrote {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
