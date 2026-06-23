"""Dependencies for API."""

from typing import Annotated

from fastapi import Depends, Query

from core import config


class PaginationParams:
    """Pagination parameters for endpoints."""

    def __init__(
        self,
        page_number: int = Query(
            default=1, ge=1, description="Номер запрашиваемой страницы."
        ),
        page_size: int = Query(
            default=config.PAGINATION_DEFAULT_PAGE_SIZE,
            ge=1,
            le=config.PAGINATION_MAX_PAGE_SIZE,
            description="Количество элементов на одной странице.",
        ),
    ):
        self.page_number = page_number
        self.page_size = page_size


PaginationDepend = Annotated[PaginationParams, Depends(PaginationParams)]
