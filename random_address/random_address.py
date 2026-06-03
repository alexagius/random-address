"""
Functions to retrieve real random addresses that geocode successfully.
"""

import logging
import math
import os
import random
import sqlite3
import sys
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


logger = logging.getLogger(__name__)
FALLBACK_OPTIONS = {"none", "postal_code", "city", "city_or_postal_code"}
EARTH_RADIUS_KM = 6371.0088
SCALE = 10_000_000


ADDRESS_SELECT = """
SELECT
    a.id,
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


@lru_cache(maxsize=1)
def _get_connection() -> sqlite3.Connection:
    """Open the packaged SQLite dataset in read-only mode."""
    package_directory = os.path.dirname(sys.modules[__name__].__file__)
    source_path = os.path.join(package_directory, "addresses-us-all.sqlite")
    try:
        connection = sqlite3.connect(
            f"file:{source_path}?mode=ro",
            uri=True,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        return connection
    except sqlite3.Error as error:
        logger.error("Error opening address database: %s", error)
        raise


def real_random_address() -> Dict[str, Any]:
    """Retrieve a random real address from the dataset."""
    total = _metadata_int("total_addresses")
    if total <= 0:
        return {}
    return _address_by_id(random.randrange(total))


def real_random_address_by_state(state_code: str) -> Dict[str, Any]:
    """Retrieve a random real address filtered by US state code."""
    state_id = _state_id(state_code)
    if state_id is None:
        return {}
    ranges = _ranges_for_filters(state=state_code)
    return _sample_one_from_ranges(ranges, random)


def real_random_address_by_postal_code(postal_code: str) -> Dict[str, Any]:
    """Retrieve a random real address filtered by US postal code."""
    ranges = _ranges_for_filters(postal_code=postal_code)
    return _sample_one_from_ranges(ranges, random)


def real_random_address_by_city(city: str) -> Dict[str, Any]:
    """Retrieve a random real address filtered by US city name."""
    ids = _candidate_ids_for_filters(city=city)
    if not ids:
        return {}
    return _address_by_id(random.choice(ids))


def real_random_addresses(
    count: int = 1,
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    city: Optional[str] = None,
    seed: Optional[int] = None,
    unique: bool = True,
    fallback: str = "city_or_postal_code",
) -> List[Dict[str, Any]]:
    """Retrieve a batch of random real addresses."""
    if count <= 0:
        return []
    if fallback not in FALLBACK_OPTIONS:
        raise ValueError(f"fallback must be one of {sorted(FALLBACK_OPTIONS)}")

    rng = random.Random(seed) if seed is not None else random
    primary_count = _candidate_count(state=state, postal_code=postal_code, city=city)

    if _should_use_fallback(
        requested_count=count,
        current_count=primary_count,
        city=city,
        postal_code=postal_code,
        fallback=fallback,
        unique=unique,
    ):
        primary_ids = _candidate_ids_for_filters(
            state=state,
            postal_code=postal_code,
            city=city,
        )
        primary_sample_ids = _sample_ids(primary_ids, count=count, rng=rng, unique=unique)
        fallback_ids = [
            address_id for address_id in _fallback_candidate_ids(
                state=state,
                postal_code=postal_code,
                city=city,
                fallback=fallback,
            )
            if address_id not in set(primary_ids)
        ]
        fallback_sample_ids = _sample_ids(
            fallback_ids,
            count=count - len(primary_sample_ids),
            rng=rng,
            unique=unique,
        )
        return _addresses_by_ids(primary_sample_ids + fallback_sample_ids)

    return _sample_addresses_for_filters(
        count=count,
        rng=rng,
        unique=unique,
        state=state,
        postal_code=postal_code,
        city=city,
    )


def real_random_address_cluster(
    count: int = 25,
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    city: Optional[str] = None,
    seed: Optional[int] = None,
    min_postal_code_count: int = 6,
    max_radius_km: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Retrieve a geographically compact group of addresses from one ZIP code."""
    if count <= 0:
        return []
    if min_postal_code_count < 1:
        raise ValueError("min_postal_code_count must be at least 1")
    if max_radius_km is not None and max_radius_km < 0:
        raise ValueError("max_radius_km must be non-negative")

    required_count = max(count, min_postal_code_count)
    rng = random.Random(seed) if seed is not None else random
    clusters = _cluster_candidates(state=state, postal_code=postal_code)
    rng.shuffle(clusters)
    city_ids = _city_ids(city) if city else []

    for cluster in clusters:
        address_ids = _cluster_address_ids(cluster["id"], city_ids=city_ids)
        if len(address_ids) < required_count:
            continue
        selected = _addresses_by_ids(address_ids[:count])
        radius = _cluster_radius_km(selected)
        if max_radius_km is None or radius <= max_radius_km:
            return selected

    return []


def list_available_states() -> List[str]:
    """Get a sorted list of all unique US state codes in the dataset."""
    return [
        row["code"]
        for row in _get_connection().execute("SELECT code FROM states ORDER BY code")
    ]


def list_available_postal_codes() -> List[str]:
    """Get a sorted list of all unique postal codes in the dataset."""
    return [
        row["code"]
        for row in _get_connection().execute("SELECT code FROM postal_codes ORDER BY code")
    ]


def list_available_cities() -> List[str]:
    """Get a sorted list of all unique city names in the dataset."""
    return [
        row["name"]
        for row in _get_connection().execute("SELECT name FROM cities ORDER BY name")
    ]


def list_states_with_counts() -> Dict[str, int]:
    """Get a dictionary of all state codes with their corresponding address counts."""
    return {
        row["code"]: row["count"]
        for row in _get_connection().execute("SELECT code, count FROM states")
    }


def list_postal_codes_with_counts() -> Dict[str, int]:
    """Get a dictionary of all postal codes with their corresponding address counts."""
    return {
        row["code"]: row["count"]
        for row in _get_connection().execute("SELECT code, count FROM postal_codes")
    }


def list_cities_with_counts() -> Dict[str, int]:
    """Get a dictionary of all city names with their corresponding address counts."""
    return {
        row["name"]: row["count"]
        for row in _get_connection().execute("SELECT name, count FROM cities")
    }


def get_summary() -> Dict[str, Any]:
    """Get a summary of the address dataset."""
    return {
        "total_addresses": _metadata_int("total_addresses"),
        "unique_states": _metadata_int("unique_states"),
        "unique_cities": _metadata_int("unique_cities"),
        "unique_postal_codes": _metadata_int("unique_postal_codes"),
    }


def _metadata_int(key: str) -> int:
    row = _get_connection().execute(
        "SELECT value FROM metadata WHERE key = ?",
        (key,),
    ).fetchone()
    return int(row["value"]) if row else 0


@lru_cache(maxsize=None)
def _state_id(state: Optional[str]) -> Optional[int]:
    if not state:
        return None
    row = _get_connection().execute(
        "SELECT id FROM states WHERE code = ?",
        (state.upper(),),
    ).fetchone()
    return int(row["id"]) if row else None


@lru_cache(maxsize=None)
def _postal_code_id(postal_code: Optional[str]) -> Optional[int]:
    if not postal_code:
        return None
    row = _get_connection().execute(
        "SELECT id FROM postal_codes WHERE code = ?",
        (str(postal_code),),
    ).fetchone()
    return int(row["id"]) if row else None


@lru_cache(maxsize=None)
def _city_ids(city: Optional[str]) -> Tuple[int, ...]:
    if not city:
        return ()
    rows = _get_connection().execute(
        "SELECT id FROM cities WHERE clean_name = ? ORDER BY id",
        (clean_text(city),),
    ).fetchall()
    return tuple(int(row["id"]) for row in rows)


def _address_by_id(address_id: int) -> Dict[str, Any]:
    row = _get_connection().execute(
        ADDRESS_SELECT + " WHERE a.id = ?",
        (address_id,),
    ).fetchone()
    return _address_from_row(row) if row else {}


def _addresses_by_ids(address_ids: Sequence[int]) -> List[Dict[str, Any]]:
    if not address_ids:
        return []
    placeholders = ",".join("?" for _ in address_ids)
    rows = _get_connection().execute(
        ADDRESS_SELECT + f" WHERE a.id IN ({placeholders})",
        tuple(address_ids),
    ).fetchall()
    by_id = {int(row["id"]): _address_from_row(row) for row in rows}
    return [by_id[address_id] for address_id in address_ids if address_id in by_id]


def _address_from_row(row: sqlite3.Row) -> Dict[str, Any]:
    return {
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


def _ranges_for_filters(
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    city: Optional[str] = None,
) -> List[Dict[str, int]]:
    state_id = _state_id(state)
    postal_code_id = _postal_code_id(postal_code)
    city_ids = _city_ids(city) if city else ()
    connection = _get_connection()

    if state and state_id is None:
        return []
    if postal_code and postal_code_id is None:
        return []
    if city and not city_ids:
        return []

    if state_id and postal_code_id and city_ids:
        return _range_rows(
            """
            SELECT start_id, end_id, count
            FROM state_postal_city_ranges
            WHERE state_id = ? AND postal_code_id = ? AND city_id IN ({})
            """,
            [state_id, postal_code_id],
            city_ids,
        )
    if state_id and postal_code_id:
        row = connection.execute(
            """
            SELECT start_id, end_id, count
            FROM state_postal_ranges
            WHERE state_id = ? AND postal_code_id = ?
            """,
            (state_id, postal_code_id),
        ).fetchone()
        return [_range_from_row(row)] if row else []
    if postal_code_id and city_ids:
        return _range_rows(
            """
            SELECT start_id, end_id, count
            FROM state_postal_city_ranges
            WHERE postal_code_id = ? AND city_id IN ({})
            """,
            [postal_code_id],
            city_ids,
        )
    if postal_code_id:
        rows = connection.execute(
            """
            SELECT start_id, end_id, count
            FROM state_postal_ranges
            WHERE postal_code_id = ?
            """,
            (postal_code_id,),
        ).fetchall()
        return [_range_from_row(row) for row in rows]
    if state_id:
        row = connection.execute(
            "SELECT start_id, end_id, count FROM state_ranges WHERE state_id = ?",
            (state_id,),
        ).fetchone()
        return [_range_from_row(row)] if row else []
    if not city:
        total = _metadata_int("total_addresses")
        return [{"start_id": 0, "end_id": total - 1, "count": total}]

    return []


def _range_rows(sql_template: str, leading_params: Sequence[int], values: Sequence[int]) -> List[Dict[str, int]]:
    placeholders = ",".join("?" for _ in values)
    rows = _get_connection().execute(
        sql_template.format(placeholders),
        tuple(leading_params) + tuple(values),
    ).fetchall()
    return [_range_from_row(row) for row in rows]


def _range_from_row(row: sqlite3.Row) -> Dict[str, int]:
    return {
        "start_id": int(row["start_id"]),
        "end_id": int(row["end_id"]),
        "count": int(row["count"]),
    }


def _sample_one_from_ranges(ranges: Sequence[Dict[str, int]], rng: Any) -> Dict[str, Any]:
    ids = _sample_ids_from_ranges(ranges, count=1, rng=rng, unique=True)
    return _address_by_id(ids[0]) if ids else {}


def _sample_addresses_for_filters(
    count: int,
    rng: Any,
    unique: bool,
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    city: Optional[str] = None,
) -> List[Dict[str, Any]]:
    ranges = _ranges_for_filters(state=state, postal_code=postal_code, city=city)
    if ranges:
        ids = _sample_ids_from_ranges(ranges, count=count, rng=rng, unique=unique)
        return _addresses_by_ids(ids)

    ids = _candidate_ids_for_filters(state=state, postal_code=postal_code, city=city)
    return _addresses_by_ids(_sample_ids(ids, count=count, rng=rng, unique=unique))


def _candidate_count(
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    city: Optional[str] = None,
) -> int:
    ranges = _ranges_for_filters(state=state, postal_code=postal_code, city=city)
    if ranges:
        return sum(item["count"] for item in ranges)
    return len(_candidate_ids_for_filters(state=state, postal_code=postal_code, city=city))


def _candidate_ids_for_filters(
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    city: Optional[str] = None,
) -> List[int]:
    ranges = _ranges_for_filters(state=state, postal_code=postal_code, city=city)
    if ranges and _range_count(ranges) <= 5000:
        return _all_ids_from_ranges(ranges)

    state_id = _state_id(state)
    postal_code_id = _postal_code_id(postal_code)
    city_ids = _city_ids(city) if city else ()
    if state and state_id is None:
        return []
    if postal_code and postal_code_id is None:
        return []
    if city and not city_ids:
        return []

    where = []
    params: List[int] = []
    if state_id is not None:
        where.append("a.state_id = ?")
        params.append(state_id)
    if postal_code_id is not None:
        where.append("a.postal_code_id = ?")
        params.append(postal_code_id)
    if city_ids:
        where.append(f"a.city_id IN ({','.join('?' for _ in city_ids)})")
        params.extend(city_ids)
    if not where:
        return _all_ids_from_ranges(_ranges_for_filters())

    rows = _get_connection().execute(
        "SELECT a.id FROM addresses a WHERE " + " AND ".join(where) + " ORDER BY a.id",
        tuple(params),
    ).fetchall()
    return [int(row["id"]) for row in rows]


def _fallback_candidate_ids(
    state: Optional[str],
    postal_code: Optional[str],
    city: Optional[str],
    fallback: str,
) -> List[int]:
    if fallback == "postal_code":
        return _candidate_ids_for_filters(state=state, postal_code=postal_code)
    if fallback == "city":
        return _candidate_ids_for_filters(state=state, city=city)

    return _dedupe_ids(
        _candidate_ids_for_filters(state=state, city=city)
        + _candidate_ids_for_filters(state=state, postal_code=postal_code)
    )


def _sample_ids_from_ranges(
    ranges: Sequence[Dict[str, int]],
    count: int,
    rng: Any,
    unique: bool,
) -> List[int]:
    total = _range_count(ranges)
    if total <= 0 or count <= 0:
        return []

    if unique:
        if count >= total:
            ids = _all_ids_from_ranges(ranges)
            rng.shuffle(ids)
            return ids
        offsets = rng.sample(range(total), count)
    else:
        offsets = [rng.randrange(total) for _ in range(count)]

    return [_id_from_offset(ranges, offset) for offset in offsets]


def _all_ids_from_ranges(ranges: Sequence[Dict[str, int]]) -> List[int]:
    ids = []
    for item in ranges:
        ids.extend(range(item["start_id"], item["end_id"] + 1))
    return ids


def _id_from_offset(ranges: Sequence[Dict[str, int]], offset: int) -> int:
    remaining = offset
    for item in ranges:
        if remaining < item["count"]:
            return item["start_id"] + remaining
        remaining -= item["count"]
    return ranges[-1]["end_id"]


def _range_count(ranges: Sequence[Dict[str, int]]) -> int:
    return sum(item["count"] for item in ranges)


def _sample_ids(ids: Sequence[int], count: int, rng: Any, unique: bool) -> List[int]:
    if not ids or count <= 0:
        return []
    if unique:
        if count >= len(ids):
            sampled = list(ids)
            rng.shuffle(sampled)
            return sampled
        return rng.sample(list(ids), count)
    return [rng.choice(ids) for _ in range(count)]


def _dedupe_ids(ids: Iterable[int]) -> List[int]:
    seen = set()
    deduped = []
    for address_id in ids:
        if address_id not in seen:
            seen.add(address_id)
            deduped.append(address_id)
    return deduped


def _cluster_candidates(
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
) -> List[Dict[str, int]]:
    state_id = _state_id(state)
    postal_code_id = _postal_code_id(postal_code)
    if state and state_id is None:
        return []
    if postal_code and postal_code_id is None:
        return []

    where = []
    params = []
    if state_id is not None:
        where.append("state_id = ?")
        params.append(state_id)
    if postal_code_id is not None:
        where.append("postal_code_id = ?")
        params.append(postal_code_id)

    sql = "SELECT id, count, radius_m FROM clusters"
    if where:
        sql += " WHERE " + " AND ".join(where)
    rows = _get_connection().execute(sql, tuple(params)).fetchall()
    return [
        {"id": int(row["id"]), "count": int(row["count"]), "radius_m": int(row["radius_m"])}
        for row in rows
    ]


def _cluster_address_ids(cluster_id: int, city_ids: Sequence[int]) -> List[int]:
    if city_ids:
        placeholders = ",".join("?" for _ in city_ids)
        rows = _get_connection().execute(
            f"""
            SELECT ca.address_id
            FROM cluster_addresses ca
            JOIN addresses a ON a.id = ca.address_id
            WHERE ca.cluster_id = ? AND a.city_id IN ({placeholders})
            ORDER BY ca.position
            """,
            (cluster_id,) + tuple(city_ids),
        ).fetchall()
    else:
        rows = _get_connection().execute(
            """
            SELECT address_id
            FROM cluster_addresses
            WHERE cluster_id = ?
            ORDER BY position
            """,
            (cluster_id,),
        ).fetchall()
    return [int(row["address_id"]) for row in rows]


def _should_use_fallback(
    requested_count: int,
    current_count: int,
    city: Optional[str],
    postal_code: Optional[str],
    fallback: str,
    unique: bool,
) -> bool:
    if fallback == "none" or not city or not postal_code:
        return False
    if unique:
        return current_count < requested_count
    return current_count == 0


def _cluster_radius_km(cluster: Sequence[Dict[str, Any]]) -> float:
    points = [
        point for point in (_coordinates(address) for address in cluster)
        if point is not None
    ]
    if not points:
        return float("inf")

    center = (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )
    return max(_haversine_km(center, point) for point in points)


def _coordinates(address: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    coordinates = address.get("coordinates") or {}
    lat = coordinates.get("lat")
    lng = coordinates.get("lng")
    if lat is None or lng is None:
        return None
    return float(lat), float(lng)


def _haversine_km(
    first: Tuple[float, float],
    second: Tuple[float, float],
) -> float:
    lat1, lng1 = first
    lat2, lng2 = second
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lng / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(haversine))


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())
