import requests


def post(base_url: str, path: str, api_key: str | None = None, json: dict | None = None, timeout: int = 10) -> dict:
    headers = {"X-API-Key": api_key} if api_key else {}
    response = requests.post(
        f"{base_url}{path}",
        headers=headers,
        json=json,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def get(base_url: str, path: str, api_key: str | None = None, params: dict | None = None, timeout: int = 10) -> dict:
    headers = {"X-API-Key": api_key} if api_key else {}
    response = requests.get(
        f"{base_url}{path}",
        headers=headers,
        params=params,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()