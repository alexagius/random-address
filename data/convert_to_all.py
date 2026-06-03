"""Export the packaged SQLite address dataset to readable JSON."""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "random_address" / "addresses-us-all.sqlite"
OUTPUT = ROOT / "addresses-us-all.json"
SCALE = 10_000_000


def main() -> int:
    connection = sqlite3.connect(SOURCE)
    connection.row_factory = sqlite3.Row
    try:
        data: Dict[str, Any] = {
            "addresses": export_addresses(connection),
            "attribution": export_attribution(connection),
        }
        clusters = export_clusters(connection)
        if clusters:
            data["clusters"] = clusters
    finally:
        connection.close()

    with OUTPUT.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.write("\n")
    print(f"Wrote {OUTPUT}")
    return 0


def export_addresses(connection: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            a.address1,
            a.address2,
            c.name AS city,
            s.code AS state,
            p.code AS postalCode,
            a.lat_e7,
            a.lng_e7
        FROM addresses a
        JOIN cities c ON c.id = a.city_id
        JOIN states s ON s.id = a.state_id
        JOIN postal_codes p ON p.id = a.postal_code_id
        ORDER BY a.id
        """
    )
    return [
        {
            "address1": row["address1"],
            "address2": row["address2"],
            "city": row["city"],
            "state": row["state"],
            "postalCode": row["postalCode"],
            "coordinates": {
                "lat": row["lat_e7"] / SCALE,
                "lng": row["lng_e7"] / SCALE,
            },
        }
        for row in rows
    ]


def export_attribution(connection: sqlite3.Connection) -> List[str]:
    return [
        row["value"]
        for row in connection.execute("SELECT value FROM attribution ORDER BY value")
    ]


def export_clusters(connection: sqlite3.Connection) -> List[Dict[str, Any]]:
    clusters = []
    rows = connection.execute(
        """
        SELECT
            cl.id,
            cl.cluster_key,
            s.code AS state,
            p.code AS postalCode,
            cl.center_lat_e7,
            cl.center_lng_e7,
            cl.radius_m,
            cl.count
        FROM clusters cl
        JOIN states s ON s.id = cl.state_id
        JOIN postal_codes p ON p.id = cl.postal_code_id
        ORDER BY cl.id
        """
    ).fetchall()

    for row in rows:
        clusters.append(
            {
                "id": row["cluster_key"],
                "state": row["state"],
                "postalCode": row["postalCode"],
                "center": {
                    "lat": row["center_lat_e7"] / SCALE,
                    "lng": row["center_lng_e7"] / SCALE,
                },
                "radius_km": row["radius_m"] / 1000,
                "count": row["count"],
                "address_indexes": export_cluster_address_indexes(connection, row["id"]),
            }
        )
    return clusters


def export_cluster_address_indexes(
    connection: sqlite3.Connection,
    cluster_id: int,
) -> List[int]:
    return [
        row["address_id"]
        for row in connection.execute(
            """
            SELECT address_id
            FROM cluster_addresses
            WHERE cluster_id = ?
            ORDER BY position
            """,
            (cluster_id,),
        )
    ]


if __name__ == "__main__":
    raise SystemExit(main())
