"""Типовые HTTP-ответы с ошибками для документации OpenAPI."""

UNAUTHORIZED = {401: {"description": "Токен истёк или отсутствует"}}
FORBIDDEN = {403: {"description": "Неверный токен или недостаточно прав"}}
NOT_FOUND = {404: {"description": "Объект не найден"}}
CONFLICT = {409: {"description": "Операция не разрешена для данного объекта"}}
DUPLICATE = {400: {"description": "Объект с такими данными уже существует"}}

AUTH_ERRORS = {**UNAUTHORIZED, **FORBIDDEN}
