"""Opt-in performance checks for the public sampling API.

Run with:
    RUN_PERFORMANCE_TESTS=1 python -m pytest tests/test_performance.py
"""

import os
from time import perf_counter

import pytest

import random_address


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_PERFORMANCE_TESTS") != "1",
    reason="performance tests are opt-in; set RUN_PERFORMANCE_TESTS=1",
)


def average_seconds_per_call(callback, iterations):
    callback()  # Warm the dataset cache and indexes outside the timing window.
    start = perf_counter()
    for _ in range(iterations):
        callback()
    return (perf_counter() - start) / iterations


def test_warm_random_address_lookup_stays_fast():
    average = average_seconds_per_call(random_address.real_random_address, iterations=1000)

    assert average < 0.001


def test_warm_postal_code_lookup_stays_fast():
    average = average_seconds_per_call(
        lambda: random_address.real_random_address_by_postal_code("06040"),
        iterations=1000,
    )

    assert average < 0.001


def test_warm_batch_sampling_stays_fast():
    average = average_seconds_per_call(
        lambda: random_address.real_random_addresses(count=25, state="NY", seed=123),
        iterations=500,
    )

    assert average < 0.003


def test_warm_cluster_sampling_stays_fast():
    average = average_seconds_per_call(
        lambda: random_address.real_random_address_cluster(
            count=25,
            postal_code="06040",
            seed=123,
        ),
        iterations=100,
    )

    assert average < 0.05
