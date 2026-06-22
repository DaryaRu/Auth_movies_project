from typing import NamedTuple


class SearchCase(NamedTuple):
    query: dict[str, str | int]
    status_code: int
    length: int


class ValidationErrorCase(NamedTuple):
    query: dict[str, str | int]
    status_code: int
    expected_field: str | None = None


class ListCase(NamedTuple):
    query: dict[str, str | int]
    status_code: int
    length: int | None = None
    body: list[dict[str, str | int]] | None = None


class DetailCase(NamedTuple):
    entity_id: str
    status_code: int
    expected_uuid: str | None = None
    expected_name: str | None = None


class SortCase(NamedTuple):
    query: dict[str, str | int]
    status_code: int
    expected_order: list[int | float | str]
