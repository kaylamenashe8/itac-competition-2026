from automation_infra.core.api.arena_api_client import post

HOLDS = "/holds"


def book_seats(base_url: str, event_id: str, seat_ids: list[str], api_key: str = None):
    return post(base_url, HOLDS, api_key, json={"event_id": event_id, "seat_ids": seat_ids})
