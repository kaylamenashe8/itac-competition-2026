import pytest
from playwright.sync_api import Page

from automation_tests.flows.web_flows.assert_on import AssertOnScreen
from automation_tests.flows.web_flows.purchase_flows.purchase_flows import PurchaseFlows

HELD_SEAT = "Seat A1, Golden, ₪140.00, held"
AVAILABLE_SEAT = "Seat B1, Golden, ₪140.00, available"
SOLD_SEAT = "Seat F1, Back, ₪60.00, sold"


@pytest.fixture
def purchase_flows(logged_in_page: Page) -> PurchaseFlows:
    return PurchaseFlows(logged_in_page)


@pytest.fixture
def assert_on(logged_in_page: Page) -> AssertOnScreen:
    return AssertOnScreen(logged_in_page)


def test_clicking_sold_seat_does_not_open_checkout(purchase_flows: PurchaseFlows, assert_on: AssertOnScreen, seating_test_event_id: str):
    purchase_flows.open_event(seating_test_event_id)
    purchase_flows.select_seat(SOLD_SEAT, force=True)

    assert_on.verify_checkout_screen_not_shown()


def test_clicking_held_seat_does_not_open_checkout(purchase_flows: PurchaseFlows, assert_on: AssertOnScreen, seating_test_event_id: str):
    purchase_flows.open_event(seating_test_event_id)
    purchase_flows.select_seat(HELD_SEAT, force=True)

    assert_on.verify_checkout_screen_not_shown()


def test_clicking_available_seat_opens_checkout(purchase_flows: PurchaseFlows, assert_on: AssertOnScreen, seating_test_event_id: str):
    purchase_flows.open_event(seating_test_event_id)
    purchase_flows.select_seat(AVAILABLE_SEAT)
    purchase_flows.continue_to_checkout()

    assert_on.verify_checkout_screen()
