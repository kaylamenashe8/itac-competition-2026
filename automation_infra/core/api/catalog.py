from automation_infra.core.api.arena_api_client import get

EVENTS = "/events"


def get_events(base_url: str, api_key: str = None, page_size: int = 50):
    return get(base_url, EVENTS, api_key, params={"page_size": page_size})


def find_event_by_name(base_url: str, name: str, api_key: str = None) -> dict:
    events = get_events(base_url, api_key)["items"]
    return next(event for event in events if event["name"] == name)
