"""
Functions to retrieve a real random address that geocode successfully
"""

import json
import logging
import math
import os
import random
import sys
import gzip
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)
FALLBACK_OPTIONS = {"none", "postal_code", "city", "city_or_postal_code"}
EARTH_RADIUS_KM = 6371.0088


@lru_cache(maxsize=1)
def _get_address_dict_list() -> Dict[str, List[Dict[str, Any]]]:
    """Load the list of addresses from a local JSON file.

    Reads the compressed 'addresses-us-all.min.json.gz' file included in the package and
    returns the data as a dictionary.

    Returns:
        dict: Dictionary containing the addresses data with the structure:
            {'addresses': [address_dict, ...]}. If an error occurs, an empty list
            under the 'addresses' key is returned.
    """
    package_directory = os.path.dirname(sys.modules[__name__].__file__)
    source_filename_path = os.path.join(package_directory, "addresses-us-all.min.json.gz")
    fallback_source_filename_path = os.path.join(package_directory, "addresses-us-all.min.json")
    try:
        if os.path.exists(source_filename_path):
            source_file_context = gzip.open(source_filename_path, "rt", encoding="utf-8")
        else:
            source_file_context = open(fallback_source_filename_path, "r", encoding="utf-8")
        with source_file_context as source_file:
            data = json.load(source_file)
            return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error("Error loading addresses: %s", e)
        return {"addresses": []}


@lru_cache(maxsize=1)
def _get_indexes() -> Dict[str, Any]:
    """Build reusable in-memory indexes over the packaged dataset."""
    addresses = _get_address_dict_list().get("addresses", [])
    by_state: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_postal_code: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_city: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_state_postal_code: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    postal_group_keys_by_state: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    postal_group_keys_by_postal_code: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    postal_group_keys_by_city: Dict[str, set] = defaultdict(set)
    precomputed_clusters_by_state_postal_code: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    precomputed_cluster_keys_by_state: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    precomputed_cluster_keys_by_postal_code: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    precomputed_cluster_keys_by_city: Dict[str, set] = defaultdict(set)
    state_counts: Counter = Counter()
    postal_code_counts: Counter = Counter()
    city_counts: Counter = Counter()

    for address in addresses:
        state = address.get("state")
        postal_code = address.get("postalCode")
        city = address.get("city")

        if state:
            by_state[state].append(address)
            state_counts[state] += 1
        if postal_code:
            by_postal_code[postal_code].append(address)
            postal_code_counts[postal_code] += 1
        if city:
            by_city[clean_text(city)].append(address)
            city_counts[city] += 1
        if state and postal_code:
            key = (state, postal_code)
            if key not in by_state_postal_code:
                postal_group_keys_by_state[state].append(key)
                postal_group_keys_by_postal_code[postal_code].append(key)
            by_state_postal_code[key].append(address)
            if city:
                postal_group_keys_by_city[clean_text(city)].add(key)

    for cluster in _get_address_dict_list().get("clusters", []):
        cluster_addresses = _cluster_addresses_from_indexes(addresses, cluster)
        if not cluster_addresses:
            continue
        state = cluster.get("state") or cluster_addresses[0].get("state")
        postal_code = cluster.get("postalCode") or cluster_addresses[0].get("postalCode")
        if not state or not postal_code:
            continue

        key = (state, postal_code)
        if key not in precomputed_clusters_by_state_postal_code:
            precomputed_cluster_keys_by_state[state].append(key)
            precomputed_cluster_keys_by_postal_code[postal_code].append(key)
        cluster_record = {
            "metadata": cluster,
            "addresses": cluster_addresses,
        }
        precomputed_clusters_by_state_postal_code[key].append(cluster_record)
        for address in cluster_addresses:
            city = address.get("city")
            if city:
                precomputed_cluster_keys_by_city[clean_text(city)].add(key)

    return {
        "addresses": addresses,
        "by_state": dict(by_state),
        "by_postal_code": dict(by_postal_code),
        "by_city": dict(by_city),
        "by_state_postal_code": dict(by_state_postal_code),
        "postal_group_keys_by_state": dict(postal_group_keys_by_state),
        "postal_group_keys_by_postal_code": dict(postal_group_keys_by_postal_code),
        "postal_group_keys_by_city": {
            city: sorted(keys) for city, keys in postal_group_keys_by_city.items()
        },
        "precomputed_clusters_by_state_postal_code": dict(precomputed_clusters_by_state_postal_code),
        "precomputed_cluster_keys_by_state": dict(precomputed_cluster_keys_by_state),
        "precomputed_cluster_keys_by_postal_code": dict(precomputed_cluster_keys_by_postal_code),
        "precomputed_cluster_keys_by_city": {
            city: sorted(keys) for city, keys in precomputed_cluster_keys_by_city.items()
        },
        "state_counts": state_counts,
        "postal_code_counts": postal_code_counts,
        "city_counts": city_counts,
    }


def _copy_address(address: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy so callers cannot mutate the cached dataset."""
    copied = dict(address)
    coordinates = address.get("coordinates")
    if isinstance(coordinates, dict):
        copied["coordinates"] = dict(coordinates)
    return copied


def _cluster_addresses_from_indexes(
    addresses: Sequence[Dict[str, Any]],
    cluster: Dict[str, Any],
) -> List[Dict[str, Any]]:
    cluster_addresses = []
    for address_index in cluster.get("address_indexes", []):
        if isinstance(address_index, int) and 0 <= address_index < len(addresses):
            cluster_addresses.append(addresses[address_index])
    return cluster_addresses


def real_random_address() -> Dict[str, Any]:
    """Retrieve a random real address from the dataset.

    Loads the dataset and returns a randomly selected address dictionary from
    the available entries.

    Returns:
        dict: Dictionary containing random address information, such as street,
        city, state, and postal code. Example:

        {
            'street': '123 Main St',
            'city': 'Los Angeles',
            'state': 'CA',
            'postalCode': '90001'
        }

        Returns an empty dictionary if no addresses are available.
    """
    addresses = _get_indexes()["addresses"]
    return _copy_address(random.choice(addresses)) if addresses else {}


def real_random_address_by_state(state_code: str) -> Dict[str, Any]:
    """Retrieve a random real address filtered by US state code.

    Args:
        state_code (str): Two-letter state abbreviation (e.g., 'CA', 'NY').

    Returns:
        dict: Dictionary containing random address information matching the
        provided state.

    Example:
        >>> import random_address
        >>> random_address.real_random_address_by_state('CA')
        {
            'address1': '37600 Sycamore Street',
            'address2': '',
            'city': 'Newark',
            'state': 'CA',
            'postalCode': '94560',
            'coordinates': {'lat': 37.5261943, 'lng': -122.0304698}
        }

        Returns an empty dictionary if no addresses match the specified state.
    """
    filtered_data = _get_indexes()["by_state"].get(state_code.upper(), [])
    return _copy_address(random.choice(filtered_data)) if filtered_data else {}


def real_random_address_by_postal_code(postal_code: str) -> Dict[str, Any]:
    """Retrieve a random real address filtered by US postal code.

    Args:
        postal_code (str): Postal code to filter the addresses by (e.g., '32409').

    Returns:
        dict: Dictionary containing random address information matching the
        provided postal code.

    Example:
        >>> import random_address
        >>> random_address.real_random_address_by_postal_code('32409')
        {
            'address1': '711 Tashanna Lane',
            'address2': '',
            'city': 'Southport',
            'state': 'FL',
            'postalCode': '32409',
            'coordinates': {'lat': 30.41437699999999, 'lng': -85.676568}
        }

        Returns an empty dictionary if no addresses match the specified postal code.
    """
    filtered_data = _get_indexes()["by_postal_code"].get(str(postal_code), [])
    return _copy_address(random.choice(filtered_data)) if filtered_data else {}


def real_random_address_by_city(city: str) -> Dict[str, Any]:
    """Retrieve a random real address filtered by US city name.

    Args:
        city (str): Name of the city to filter the addresses by (e.g., 'Newark').

    Returns:
        dict: Dictionary containing random address information matching the
        provided city.

    Example:
        >>> import random_address
        >>> random_address.real_random_address_by_city('Newark')
        {
            'address1': '37600 Sycamore Street',
            'address2': '',
            'city': 'Newark',
            'state': 'CA',
            'postalCode': '94560',
            'coordinates': {'lat': 37.5261943, 'lng': -122.0304698}
        }

        Returns an empty dictionary if no addresses match the specified city.
    """
    filtered_data = _get_indexes()["by_city"].get(clean_text(city), [])
    return _copy_address(random.choice(filtered_data)) if filtered_data else {}


def real_random_addresses(
    count: int = 1,
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    city: Optional[str] = None,
    seed: Optional[int] = None,
    unique: bool = True,
    fallback: str = "city_or_postal_code",
) -> List[Dict[str, Any]]:
    """Retrieve a batch of random real addresses.

    Args:
        count (int): Maximum number of addresses to return.
        state (str, optional): Two-letter state abbreviation.
        postal_code (str, optional): Five-digit postal code.
        city (str, optional): City name.
        seed (int, optional): Random seed for reproducible batches.
        unique (bool): Return each matching address at most once when True.
        fallback (str): How to fill a short result when both city and
            postal_code are provided. Defaults to "city_or_postal_code".
            Supported values are "none", "postal_code", "city", and
            "city_or_postal_code".

    Returns:
        list: Random address dictionaries matching the requested filters.
    """
    if count <= 0:
        return []
    if fallback not in FALLBACK_OPTIONS:
        raise ValueError(f"fallback must be one of {sorted(FALLBACK_OPTIONS)}")

    primary_matches = _candidate_addresses(
        state=state,
        postal_code=postal_code,
        city=city,
    )

    if _should_use_fallback(
        requested_count=count,
        current_count=len(primary_matches),
        city=city,
        postal_code=postal_code,
        fallback=fallback,
        unique=unique,
    ):
        rng = random.Random(seed) if seed is not None else random
        primary_sample = _sample_addresses(
            primary_matches,
            count=count,
            rng=rng,
            unique=unique,
        )
        primary_keys = {_address_identity(address) for address in primary_matches}
        fallback_matches = [
            address for address in _fallback_candidate_addresses(
                state=state,
                postal_code=postal_code,
                city=city,
                fallback=fallback,
            )
            if _address_identity(address) not in primary_keys
        ]
        fallback_sample = _sample_addresses(
            fallback_matches,
            count=count - len(primary_sample),
            rng=rng,
            unique=unique,
        )
        return [_copy_address(address) for address in primary_sample + fallback_sample]

    rng = random.Random(seed) if seed is not None else random
    return [
        _copy_address(address)
        for address in _sample_addresses(primary_matches, count=count, rng=rng, unique=unique)
    ]


def real_random_address_cluster(
    count: int = 25,
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    city: Optional[str] = None,
    seed: Optional[int] = None,
    min_postal_code_count: int = 6,
    max_radius_km: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Retrieve a geographically compact group of addresses from one ZIP code.

    Candidate ZIP groups must contain at least ``count`` records and at least
    ``min_postal_code_count`` records after optional state, ZIP, and city
    filters. Within the selected ZIP, the function returns the nearest
    ``count`` addresses around the densest available anchor point.
    """
    if count <= 0:
        return []
    if min_postal_code_count < 1:
        raise ValueError("min_postal_code_count must be at least 1")
    if max_radius_km is not None and max_radius_km < 0:
        raise ValueError("max_radius_km must be non-negative")

    required_count = max(count, min_postal_code_count)
    precomputed_clusters = [
        cluster for cluster in _precomputed_cluster_candidates(
            state=state,
            postal_code=postal_code,
            city=city,
        )
        if len(cluster["addresses"]) >= required_count
    ]
    if precomputed_clusters:
        rng = random.Random(seed) if seed is not None else random
        rng.shuffle(precomputed_clusters)
        for cluster in precomputed_clusters:
            selected = cluster["addresses"][:count]
            radius = _cluster_radius_km(selected)
            if max_radius_km is None or radius <= max_radius_km:
                return [_copy_address(address) for address in selected]
        return []

    groups = [
        group for group in _cluster_candidate_groups(
            state=state,
            postal_code=postal_code,
            city=city,
        )
        if len(group) >= required_count
    ]
    if not groups:
        return []

    rng = random.Random(seed) if seed is not None else random
    rng.shuffle(groups)

    best_over_radius: Optional[Tuple[float, List[Dict[str, Any]]]] = None
    for group in groups:
        cluster = _nearest_cluster(group, count=count, rng=rng)
        radius = _cluster_radius_km(cluster)
        if max_radius_km is None or radius <= max_radius_km:
            return [_copy_address(address) for address in cluster]
        if best_over_radius is None or radius < best_over_radius[0]:
            best_over_radius = (radius, cluster)

    return []


def _precomputed_cluster_candidates(
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    city: Optional[str] = None,
) -> List[Dict[str, Any]]:
    indexes = _get_indexes()
    state_code = state.upper() if state else None
    postal = str(postal_code) if postal_code else None
    city_key = clean_text(city) if city else None

    if state_code and postal:
        keys = [(state_code, postal)]
    elif postal:
        keys = indexes["precomputed_cluster_keys_by_postal_code"].get(postal, [])
    elif state_code:
        if city_key:
            keys = [
                key for key in indexes["precomputed_cluster_keys_by_city"].get(city_key, [])
                if key[0] == state_code
            ]
        else:
            keys = indexes["precomputed_cluster_keys_by_state"].get(state_code, [])
    elif city_key:
        keys = indexes["precomputed_cluster_keys_by_city"].get(city_key, [])
    else:
        keys = list(indexes["precomputed_clusters_by_state_postal_code"].keys())

    clusters = []
    for key in keys:
        for cluster in indexes["precomputed_clusters_by_state_postal_code"].get(key, []):
            addresses = cluster["addresses"]
            if city_key:
                addresses = [
                    address for address in addresses
                    if clean_text(address.get("city")) == city_key
                ]
            if addresses:
                clusters.append({
                    "metadata": cluster["metadata"],
                    "addresses": addresses,
                })
    return clusters


def _candidate_addresses(
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    city: Optional[str] = None,
) -> List[Dict[str, Any]]:
    indexes = _get_indexes()
    if postal_code:
        candidates = indexes["by_postal_code"].get(str(postal_code), [])
        if not state and not city:
            return candidates
    elif city:
        candidates = indexes["by_city"].get(clean_text(city), [])
        if not state:
            return candidates
    elif state:
        candidates = indexes["by_state"].get(state.upper(), [])
        return candidates
    else:
        candidates = indexes["addresses"]
        return candidates

    return [
        address for address in candidates
        if _address_matches(address, state=state, postal_code=postal_code, city=city)
    ]


def _fallback_candidate_addresses(
    state: Optional[str],
    postal_code: Optional[str],
    city: Optional[str],
    fallback: str,
) -> List[Dict[str, Any]]:
    indexes = _get_indexes()
    if fallback == "postal_code":
        candidates = indexes["by_postal_code"].get(str(postal_code), [])
    elif fallback == "city":
        candidates = indexes["by_city"].get(clean_text(city), [])
    else:
        candidates = _dedupe_address_sequence(
            list(indexes["by_city"].get(clean_text(city), []))
            + list(indexes["by_postal_code"].get(str(postal_code), []))
        )

    return [
        address for address in candidates
        if _address_matches_fallback(
            address,
            state=state,
            postal_code=postal_code,
            city=city,
            fallback=fallback,
        )
    ]


def _dedupe_address_sequence(addresses: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped = []
    for address in addresses:
        key = _address_identity(address)
        if key not in seen:
            seen.add(key)
            deduped.append(address)
    return deduped


def _cluster_candidate_groups(
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    city: Optional[str] = None,
) -> List[List[Dict[str, Any]]]:
    indexes = _get_indexes()
    state_code = state.upper() if state else None
    postal = str(postal_code) if postal_code else None
    city_key = clean_text(city) if city else None

    if state_code and postal:
        keys = [(state_code, postal)]
    elif postal:
        keys = indexes["postal_group_keys_by_postal_code"].get(postal, [])
    elif state_code:
        if city_key:
            keys = [
                key for key in indexes["postal_group_keys_by_city"].get(city_key, [])
                if key[0] == state_code
            ]
        else:
            keys = indexes["postal_group_keys_by_state"].get(state_code, [])
    elif city_key:
        keys = indexes["postal_group_keys_by_city"].get(city_key, [])
    else:
        keys = list(indexes["by_state_postal_code"].keys())

    groups = []
    for key in keys:
        group = indexes["by_state_postal_code"].get(key, [])
        if city_key:
            group = [
                address for address in group
                if clean_text(address.get("city")) == city_key
            ]
        if group:
            groups.append(group)
    return groups


def _nearest_cluster(
    addresses: Sequence[Dict[str, Any]],
    count: int,
    rng: Any,
) -> List[Dict[str, Any]]:
    eligible = [address for address in addresses if _coordinates(address) is not None]
    if len(eligible) <= count:
        return list(eligible)

    anchors = list(eligible)
    rng.shuffle(anchors)
    best_score: Optional[Tuple[float, float]] = None
    best_cluster: List[Dict[str, Any]] = []

    for anchor in anchors:
        anchor_coordinates = _coordinates(anchor)
        if anchor_coordinates is None:
            continue
        distances = []
        for index, candidate in enumerate(eligible):
            candidate_coordinates = _coordinates(candidate)
            if candidate_coordinates is not None:
                distances.append((
                    _haversine_km(anchor_coordinates, candidate_coordinates),
                    index,
                    candidate,
                ))

        distances.sort(key=lambda item: (item[0], item[1]))
        nearest = distances[:count]
        max_distance = nearest[-1][0]
        average_distance = sum(item[0] for item in nearest) / len(nearest)
        score = (max_distance, average_distance)
        if best_score is None or score < best_score:
            best_score = score
            best_cluster = [item[2] for item in nearest]

    return best_cluster


def _coordinates(address: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    coordinates = address.get("coordinates") or {}
    lat = coordinates.get("lat")
    lng = coordinates.get("lng")
    if lat is None or lng is None:
        return None
    return float(lat), float(lng)


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


def _address_matches(
    address: Dict[str, Any],
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    city: Optional[str] = None,
) -> bool:
    if state and address.get("state") != state.upper():
        return False
    if postal_code and address.get("postalCode") != str(postal_code):
        return False
    if city and clean_text(address.get("city")) != clean_text(city):
        return False
    return True


def _address_matches_fallback(
    address: Dict[str, Any],
    state: Optional[str],
    postal_code: Optional[str],
    city: Optional[str],
    fallback: str,
) -> bool:
    if state and address.get("state") != state.upper():
        return False

    matches_postal_code = address.get("postalCode") == str(postal_code)
    matches_city = clean_text(address.get("city")) == clean_text(city)
    if fallback == "postal_code":
        return matches_postal_code
    if fallback == "city":
        return matches_city
    return matches_city or matches_postal_code


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


def _sample_addresses(
    addresses: List[Dict[str, Any]],
    count: int,
    rng: Any,
    unique: bool,
) -> List[Dict[str, Any]]:
    if not addresses or count <= 0:
        return []

    if unique:
        if count >= len(addresses):
            shuffled = list(addresses)
            rng.shuffle(shuffled)
            return shuffled
        return rng.sample(addresses, count)

    return [rng.choice(addresses) for _ in range(count)]


def _address_identity(address: Dict[str, Any]) -> tuple:
    return (
        clean_text(address.get("address1")),
        clean_text(address.get("address2")),
        clean_text(address.get("city")),
        address.get("state"),
        address.get("postalCode"),
    )


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def list_available_states() -> List[str]:
    """Get a sorted list of all unique US state codes in the dataset.

    Returns:
        List[str]: Alphabetically sorted list of unique state codes.
    """
    return sorted(_get_indexes()["state_counts"])


def list_available_postal_codes() -> List[str]:
    """Get a sorted list of all unique postal codes in the dataset.

    Returns:
        List[str]: Alphabetically sorted list of unique postal codes.
    """
    return sorted(_get_indexes()["postal_code_counts"])


def list_available_cities() -> List[str]:
    """Get a sorted list of all unique city names in the dataset.

    Returns:
        List[str]: Alphabetically sorted list of unique cities.
    """
    return sorted(_get_indexes()["city_counts"])


def list_states_with_counts() -> Dict[str, int]:
    """Get a dictionary of all state codes with their corresponding address counts.

    Returns:
        Dict[str, int]: Dictionary with state codes as keys and counts as values.
    """
    return dict(_get_indexes()["state_counts"])


def list_postal_codes_with_counts() -> Dict[str, int]:
    """Get a dictionary of all postal codes with their corresponding address counts.

    Returns:
        Dict[str, int]: Dictionary with postal codes as keys and counts as values.
    """
    return dict(_get_indexes()["postal_code_counts"])


def list_cities_with_counts() -> Dict[str, int]:
    """Get a dictionary of all city names with their corresponding address counts.

    Returns:
        Dict[str, int]: Dictionary with city names as keys and counts as values.
    """
    return dict(_get_indexes()["city_counts"])


def get_summary() -> Dict[str, Any]:
    """Get a summary of the address dataset.

    Returns:
        Dict[str, Any]: Dictionary summarizing number of addresses, states, cities, and postal codes.
    """
    indexes = _get_indexes()
    addresses = indexes["addresses"]
    return {
        "total_addresses": len(addresses),
        "unique_states": len(indexes["state_counts"]),
        "unique_cities": len(indexes["city_counts"]),
        "unique_postal_codes": len(indexes["postal_code_counts"]),
    }
