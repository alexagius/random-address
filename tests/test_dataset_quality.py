from functools import lru_cache
from pathlib import Path
import sqlite3


DATASET_PATH = Path(__file__).resolve().parents[1] / "random_address" / "addresses-us-all.sqlite"


@lru_cache(maxsize=1)
def connection():
    db = sqlite3.connect(DATASET_PATH)
    db.row_factory = sqlite3.Row
    return db


def address_rows():
    return connection().execute(
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
        """
    )


def test_packaged_records_are_complete():
    for address in address_rows():
        assert address["address1"]
        assert address["city"]
        assert address["state"]
        assert address["postalCode"]
        assert address["postalCode"].isdigit()
        assert len(address["postalCode"]) == 5
        assert address["postalCode"] not in {"00000", "99999"}
        assert isinstance(address["lat_e7"], int)
        assert isinstance(address["lng_e7"], int)


def test_packaged_records_include_address2_values():
    count = connection().execute(
        "SELECT COUNT(*) FROM addresses WHERE address2 <> ''"
    ).fetchone()[0]
    assert count > 100000


def test_packaged_records_have_broad_zip_coverage():
    postal_counts = [
        row[0]
        for row in connection().execute(
            "SELECT count FROM postal_codes"
        )
    ]

    assert len(postal_counts) > 26000
    assert sum(1 for count in postal_counts if count >= 5) > 24000
    assert sum(1 for count in postal_counts if count >= 10) > 24000
    assert sum(1 for count in postal_counts if count >= 25) > 23000
    assert sum(1 for count in postal_counts if count >= 35) > 23000


def test_packaged_records_include_new_hampshire():
    nh_addresses = connection().execute(
        """
        SELECT COUNT(*)
        FROM addresses a
        JOIN states s ON s.id = a.state_id
        WHERE s.code = 'NH'
        """
    ).fetchone()[0]
    nh_postal_codes = connection().execute(
        """
        SELECT COUNT(DISTINCT a.postal_code_id)
        FROM addresses a
        JOIN states s ON s.id = a.state_id
        WHERE s.code = 'NH'
        """
    ).fetchone()[0]

    assert nh_addresses > 2000
    assert nh_postal_codes > 200


def test_packaged_records_include_precomputed_clusters():
    cluster_count = connection().execute(
        "SELECT COUNT(*) FROM clusters"
    ).fetchone()[0]
    non_35_clusters = connection().execute(
        "SELECT COUNT(*) FROM clusters WHERE count != 35"
    ).fetchone()[0]
    non_35_cluster_addresses = connection().execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT cluster_id, COUNT(*) AS row_count
            FROM cluster_addresses
            GROUP BY cluster_id
            HAVING row_count != 35
        )
        """
    ).fetchone()[0]
    invalid_address_ids = connection().execute(
        """
        SELECT COUNT(*)
        FROM cluster_addresses ca
        LEFT JOIN addresses a ON a.id = ca.address_id
        WHERE a.id IS NULL
        """
    ).fetchone()[0]
    mismatched_cluster_addresses = connection().execute(
        """
        SELECT COUNT(*)
        FROM cluster_addresses ca
        JOIN addresses a ON a.id = ca.address_id
        JOIN clusters c ON c.id = ca.cluster_id
        WHERE a.state_id != c.state_id
            OR a.postal_code_id != c.postal_code_id
        """
    ).fetchone()[0]

    assert cluster_count > 23000
    assert non_35_clusters == 0
    assert non_35_cluster_addresses == 0
    assert invalid_address_ids == 0
    assert mismatched_cluster_addresses == 0
