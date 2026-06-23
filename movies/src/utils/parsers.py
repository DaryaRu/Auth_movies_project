"""Utility functions."""


def parse_sort_param(sort_str: str) -> tuple[str, str]:
    """Parse '-field' / 'field' into (field, order) for ES sort."""
    order = "desc" if sort_str.startswith("-") else "asc"
    field = sort_str.lstrip("-")
    return field, order
