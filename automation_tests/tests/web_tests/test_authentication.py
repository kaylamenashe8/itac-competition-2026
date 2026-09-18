import os
import uuid

import pytest
from playwright.sync_api import Page

from automation_tests.flows.web_flows.authenitication_flows.authentication_flows import AuthenticationFlows
from automation_tests.flows.web_flows.assert_on import AssertOnScreen

TEST_USER_EMAIL = os.environ["TEST_USER_EMAIL"]
TEST_USER_PASSWORD = os.environ["TEST_USER_PASSWORD"]

pytestmark = pytest.mark.no_auto_login


@pytest.fixture
def auth_flows(page: Page, base_url: str) -> AuthenticationFlows:
    page.goto(base_url)
    return AuthenticationFlows(page)


@pytest.fixture
def assert_on(page: Page) -> AssertOnScreen:
    return AssertOnScreen(page)


def test_login_with_valid_credentials(auth_flows: AuthenticationFlows, assert_on: AssertOnScreen):
    auth_flows.login(TEST_USER_EMAIL, TEST_USER_PASSWORD)

    assert_on.verify_events_main_screen()



@pytest.mark.skip(reason="needs more robust solution before unskipping to logout/reset before attempting test")
def test_register_new_account(auth_flows: AuthenticationFlows, assert_on: AssertOnScreen):
    new_email = f"kaylamenashe-{uuid.uuid4().hex[:10]}@gmail.com"

    auth_flows.register(new_email, TEST_USER_PASSWORD)

    assert_on.verify_events_main_screen()



