"""Валидаторы для шаблонов уведомлений."""

from dataclasses import dataclass
from typing import Literal

from jinja2 import Environment, TemplateSyntaxError, meta

Channel = Literal["email", "sms", "push"]

_env = Environment()


@dataclass
class ValidationResult:
    """Результат валидации шаблона."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]


def _used_variables(text: str) -> set[str]:
    """Переменные, реально используемые в Jinja2-шаблоне."""
    ast = _env.parse(text)
    return meta.find_undeclared_variables(ast)


def validate_template(
    code: str,
    name: str,
    channel: str,
    subject: str | None,
    body: str,
    allowed_variables: list[str],
) -> ValidationResult:
    """Валидировать шаблон: обязательные поля, канал, синтаксис Jinja2,
    соответствие используемых переменных allowed_variables.
    """
    errors = []
    warnings = []

    if not code:
        errors.append("Code is required")
    if not name:
        errors.append("Name is required")
    if not body:
        errors.append("Body is required")

    valid_channels = ["email", "sms", "push"]
    if channel not in valid_channels:
        errors.append(
            f"Invalid channel: {channel}. Must be one of: {', '.join(valid_channels)}"
        )

    all_used_variables: set[str] = set()
    for label, text in (("body", body), ("subject", subject or "")):
        try:
            all_used_variables |= _used_variables(text)
        except TemplateSyntaxError as e:
            errors.append(f"Invalid syntax in {label}: {e}")

    allowed_set = set(allowed_variables)
    for var in all_used_variables:
        if var not in allowed_set:
            errors.append(
                f"Variable '{var}' is used in template but not in allowed_variables"
            )

    for var in allowed_variables:
        if var not in all_used_variables:
            warnings.append(
                f"Variable '{var}' is in allowed_variables but not used in template"
            )

    is_valid = len(errors) == 0

    return ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
    )
