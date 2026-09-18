from automation_infra.core.api.arena_api_client import get

HEALTH = "/health"
ME = "/me"


def get_service_health(base_url: str) -> dict:
    # no api key needed for this endpoint, just checks the server health
    return get(base_url, HEALTH)


def get_me(base_url: str, api_key: str) -> dict:
    # gets the user entity --> organizer or fan
    return get(base_url, ME, api_key)
