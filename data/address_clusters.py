"""Build compact ZIP-level address clusters for the packaged dataset."""

import math
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple


Address = Dict[str, Any]
EARTH_RADIUS_KM = 6371.0088


def build_clusters(
    addresses: Sequence[Address],
    cluster_size: int = 35,
    min_postal_code_count: int = 6,
) -> List[Dict[str, Any]]:
    """Build one compact cluster per state/ZIP group when enough records exist."""
    if cluster_size < 1:
        raise ValueError("cluster_size must be at least 1")
    if min_postal_code_count < 1:
        raise ValueError("min_postal_code_count must be at least 1")

    index_by_object = {id(address): index for index, address in enumerate(addresses)}
    groups = group_by_state_postal_code(addresses)
    required_count = max(cluster_size, min_postal_code_count)
    clusters = []

    for cluster_number, key in enumerate(sorted(groups), start=1):
        group = groups[key]
        if len(group) < required_count:
            continue

        cluster_addresses = nearest_cluster(group, count=cluster_size)
        address_indexes = [index_by_object[id(address)] for address in cluster_addresses]
        center = cluster_center(cluster_addresses)
        radius_km = cluster_radius_km(cluster_addresses, center)
        state, postal_code = key

        clusters.append({
            "id": f"{state}-{postal_code}-{cluster_number:05d}",
            "state": state,
            "postalCode": postal_code,
            "count": len(address_indexes),
            "center": {
                "lat": round(center[0], 7),
                "lng": round(center[1], 7),
            },
            "radius_km": round(radius_km, 4),
            "cities": sorted({
                address.get("city", "")
                for address in cluster_addresses
                if address.get("city")
            }),
            "address_indexes": address_indexes,
        })

    return clusters


def attach_clusters(
    data: Dict[str, Any],
    cluster_size: int = 35,
    min_postal_code_count: int = 6,
) -> Dict[str, Any]:
    """Attach regenerated cluster metadata to a loaded dataset dictionary."""
    data["clusters"] = build_clusters(
        data.get("addresses", []),
        cluster_size=cluster_size,
        min_postal_code_count=min_postal_code_count,
    )
    return data


def group_by_state_postal_code(
    addresses: Sequence[Address],
) -> Dict[Tuple[str, str], List[Address]]:
    groups: Dict[Tuple[str, str], List[Address]] = defaultdict(list)
    for address in addresses:
        state = address.get("state")
        postal_code = address.get("postalCode")
        if state and postal_code and coordinates(address) is not None:
            groups[(state, postal_code)].append(address)
    return dict(groups)


def nearest_cluster(addresses: Sequence[Address], count: int) -> List[Address]:
    """Return the densest nearest-neighbor window from a state/ZIP group."""
    eligible = [address for address in addresses if coordinates(address) is not None]
    if len(eligible) <= count:
        return sorted(eligible, key=address_sort_key)

    best_score: Optional[Tuple[float, float, Tuple[str, str, str, str, str]]] = None
    best_cluster: List[Address] = []

    for anchor in sorted(eligible, key=address_sort_key):
        anchor_coordinates = coordinates(anchor)
        if anchor_coordinates is None:
            continue
        distances = []
        for candidate in eligible:
            candidate_coordinates = coordinates(candidate)
            if candidate_coordinates is not None:
                distances.append((
                    haversine_km(anchor_coordinates, candidate_coordinates),
                    address_sort_key(candidate),
                    candidate,
                ))

        distances.sort(key=lambda item: (item[0], item[1]))
        nearest = distances[:count]
        max_distance = nearest[-1][0]
        average_distance = sum(item[0] for item in nearest) / len(nearest)
        score = (max_distance, average_distance, address_sort_key(anchor))
        if best_score is None or score < best_score:
            best_score = score
            best_cluster = [item[2] for item in nearest]

    return best_cluster


def coordinates(address: Address) -> Optional[Tuple[float, float]]:
    point = address.get("coordinates") or {}
    lat = point.get("lat")
    lng = point.get("lng")
    if lat is None or lng is None:
        return None
    return float(lat), float(lng)


def cluster_center(addresses: Sequence[Address]) -> Tuple[float, float]:
    points = [point for point in (coordinates(address) for address in addresses) if point]
    if not points:
        return 0.0, 0.0
    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )


def cluster_radius_km(
    addresses: Sequence[Address],
    center: Optional[Tuple[float, float]] = None,
) -> float:
    points = [point for point in (coordinates(address) for address in addresses) if point]
    if not points:
        return 0.0
    center = center or cluster_center(addresses)
    return max(haversine_km(center, point) for point in points)


def haversine_km(first: Tuple[float, float], second: Tuple[float, float]) -> float:
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


def address_sort_key(address: Address) -> Tuple[str, str, str, str, str]:
    return (
        str(address.get("state") or ""),
        str(address.get("postalCode") or ""),
        clean(address.get("city")),
        clean(address.get("address1")),
        clean(address.get("address2")),
    )


def clean(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())
