"""
Tests for random_address module
"""
import pytest

from random_address import real_random_address
from random_address import real_random_addresses
from random_address import real_random_address_by_state
from random_address import real_random_address_by_postal_code
from random_address import list_available_states


def test_real_random_address():
    """Test default return as TRUE"""
    assert real_random_address()


def test_real_random_address_return_dict():
    """Test type of return as dict"""
    assert isinstance(real_random_address(), dict)


def test_real_random_address_num_fields():
    """Test number of elements of dict returned"""
    assert len(real_random_address()) == 6


def test_real_random_address_fields():
    """Test that the random address has all expected fields"""
    address = real_random_address()
    expected_fields = {'address1', 'address2', 'city', 'state', 'postalCode', 'coordinates'}
    assert expected_fields == set(address.keys())


def test_real_random_address_by_state():
    """Test return with a valid state code and validate content"""
    for state in ['CA', 'FL', 'AK', 'NY', 'TX', 'MT']:
        address = real_random_address_by_state(state)
        assert isinstance(address, dict)
        assert address.get('state') == state


def test_real_random_address_by_state_with_no_results():
    """Test return with a state code with no results"""
    assert not real_random_address_by_state('ZZ')


def test_list_available_states_includes_complete_coverage_states():
    """Test represented states are complete enough for this dataset."""
    expected_states = {
        'AK', 'AL', 'AR', 'AZ', 'CA', 'CO', 'CT', 'DC', 'DE', 'FL',
        'GA', 'HI', 'IA', 'ID', 'IL', 'IN', 'KS', 'KY', 'LA', 'MA',
        'MD', 'ME', 'MI', 'MN', 'MO', 'MS', 'MT', 'NC', 'ND', 'NE',
        'NH', 'NJ', 'NM', 'NV', 'NY', 'OH', 'OK', 'OR', 'PA', 'RI',
        'SC', 'SD', 'TN', 'TX', 'UT', 'VA', 'VT', 'WA', 'WI', 'WV',
        'WY',
    }
    assert set(list_available_states()) == expected_states


def test_real_random_address_by_postal_code():
    """Test return with a valid postal code and validate content"""
    postal_codes = ['99577', '32409', '94560']
    for code in postal_codes:
        address = real_random_address_by_postal_code(code)
        assert isinstance(address, dict)
        assert address.get('postalCode') == code


def test_real_random_address_by_postal_code_with_no_results():
    """Test return with a postal code with no results"""
    assert not real_random_address_by_postal_code('00000')


def test_real_random_addresses_returns_seeded_batch():
    """Test batch helper returns reproducible batches."""
    first_batch = real_random_addresses(count=5, state='NH', seed=123)
    second_batch = real_random_addresses(count=5, state='NH', seed=123)

    assert len(first_batch) == 5
    assert first_batch == second_batch
    assert all(address.get('state') == 'NH' for address in first_batch)


def test_real_random_addresses_default_fallback_expands_short_city_zip_match():
    """Test default fallback fills from same city or ZIP when exact match is short."""
    strict_matches = real_random_addresses(
        count=20,
        state='KY',
        postal_code='40214',
        city='Louisville',
        fallback='none',
        seed=123,
    )
    fallback_matches = real_random_addresses(
        count=20,
        state='KY',
        postal_code='40214',
        city='Louisville',
        seed=123,
    )

    assert 0 < len(strict_matches) < 20
    assert len(fallback_matches) == 20
    assert all(address in fallback_matches for address in strict_matches)
    assert all(address.get('state') == 'KY' for address in fallback_matches)
    assert all(
        address.get('postalCode') == '40214'
        or address.get('city', '').lower() == 'louisville'
        for address in fallback_matches
    )
    assert any(
        address.get('postalCode') != '40214'
        or address.get('city', '').lower() != 'louisville'
        for address in fallback_matches
    )


def test_real_random_addresses_can_fallback_to_postal_code_only():
    """Test postal-code fallback keeps the ZIP hard-filtered."""
    addresses = real_random_addresses(
        count=10,
        state='KY',
        postal_code='40214',
        city='Louisville',
        fallback='postal_code',
        seed=123,
    )

    assert len(addresses) == 10
    assert all(address.get('state') == 'KY' for address in addresses)
    assert all(address.get('postalCode') == '40214' for address in addresses)


def test_real_random_addresses_rejects_unknown_fallback():
    """Test fallback names are validated."""
    with pytest.raises(ValueError):
        real_random_addresses(count=1, fallback='nearby')
