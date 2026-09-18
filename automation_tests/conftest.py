import os
import pytest
from dotenv import load_dotenv
from playwright.sync_api import Browser, Page

from automation_infra.core.api.catalog import find_event_by_name
from automation_infra.core.api.test_hooks import reset_workspace
from automation_tests.entities.user_entitites import FAN, ORGANIZER
from automation_tests.flows.web_flows.authenitication_flows.authentication_flows import AuthenticationFlows

load_dotenv()

pytest_plugins = ["automation_tests.flows.fixtures"]

API_BASE_URL = os.environ.get(
    "ARENA_API_BASE_URL",
    "https://project--ac0e6745-4110-4788-8049-64a6a057c641.lovable.app/api/public/v1",
)
WEB_BASE_URL = os.environ.get(
    "ARENA_WEB_BASE_URL",
    "https://arena.itac.co.il/",
)

USERS = {"organizer": ORGANIZER, "fan": FAN}


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "no_auto_login: opt out of the autouse per-session login fixture",
    )


@pytest.fixture(scope="session")
def active_user():
    return USERS[os.environ.get("active_user", "organizer")]


@pytest.fixture(scope="session")
def base_url():
    return WEB_BASE_URL


@pytest.fixture(scope="session")
def api_base_url():
    return API_BASE_URL


@pytest.fixture(scope="session", autouse=True)
def reset_workspace_via_api(active_user):
    reset_workspace(API_BASE_URL, active_user.api_key)


@pytest.fixture(scope="session")
def logged_in_page(browser: Browser, base_url: str, active_user) -> Page:
    context = browser.new_context(base_url=base_url)
    page = context.new_page()
    page.goto("login")
    AuthenticationFlows(page).login(active_user.email, active_user.password)
    page.wait_for_url(lambda url: "/login" not in url, timeout=15000)

    yield page

    context.close()


@pytest.fixture(scope="session")
def seating_test_event_id(api_base_url, active_user, reset_workspace_via_api) -> str:
    return find_event_by_name(api_base_url, "Off By One", active_user.api_key)["id"]


@pytest.fixture(autouse=True)
def _ensure_logged_in(request):
    if request.node.get_closest_marker("no_auto_login"):
        return
    request.getfixturevalue("logged_in_page")


