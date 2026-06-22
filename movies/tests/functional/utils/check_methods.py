"""Module for check methods for tests."""


async def assert_status_return_json(response, status) -> dict | list:
    """
    Checks responce status, return responce.json
    """
    assert response.status == status
    return await response.json()


async def assert_cache_isolated(http_client, url_1: str, url_2: str) -> None:
    """Assert that url_1 and url_2 have separate cache keys."""
    response_1 = await http_client.get(url_1)
    assert response_1.headers["X-FastAPI-Cache"] == "MISS"

    response_2 = await http_client.get(url_1)
    assert response_2.headers["X-FastAPI-Cache"] == "HIT"

    response_3 = await http_client.get(url_2)
    assert response_3.headers["X-FastAPI-Cache"] == "MISS"


def assert_required_fields(obj: dict, fields: set) -> None:
    """
    Asserts that all required fields are present in the dictionary.
    """
    assert fields.issubset(obj.keys()), (
        f"Missing fields: {fields - obj.keys()}"
    )
