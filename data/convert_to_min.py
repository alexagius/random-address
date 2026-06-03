"""Build the packaged SQLite address dataset from readable JSON."""

from pathlib import Path

from build_sqlite_dataset import build_sqlite_dataset


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "addresses-us-all.json"
OUTPUT = ROOT / "random_address" / "addresses-us-all.sqlite"


def main() -> int:
    if not SOURCE.exists():
        raise SystemExit(f"Source dataset not found: {SOURCE}")
    build_sqlite_dataset(SOURCE, OUTPUT)
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
