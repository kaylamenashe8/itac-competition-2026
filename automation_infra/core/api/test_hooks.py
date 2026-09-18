from automation_infra.core.api.arena_api_client import post

RESET = "/reset"
EXPIRE_HOLDS = "/test/expire-holds"


def reset_workspace(base_url: str, api_key: str) -> dict:
    return post(base_url, RESET, api_key)


def expire_all_holds(base_url: str, api_key: str) -> dict:
    return post(base_url, EXPIRE_HOLDS, api_key)