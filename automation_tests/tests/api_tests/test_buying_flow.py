import pytest

from automation_tests.flows.api_flows.buying_flow_flows import (
    book_mixed_available_and_unavailable_seats,
    book_only_available_seats,
    book_only_unavailable_seats,
)


@pytest.mark.no_auto_login
def test_only_available_seats(api_base_url, active_user):
    assert book_only_available_seats(api_base_url, active_user.api_key)


@pytest.mark.no_auto_login
def test_only_unavailable_seats(api_base_url, active_user):
    assert not book_only_unavailable_seats(api_base_url, active_user.api_key)


@pytest.mark.no_auto_login
def test_mixed_available_and_unavailable_seats(api_base_url, active_user):
    assert not book_mixed_available_and_unavailable_seats(api_base_url, active_user.api_key)
