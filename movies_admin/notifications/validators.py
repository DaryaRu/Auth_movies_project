"""Валидаторы для шаблонов уведомлений."""

import re
from dataclasses import dataclass
from typing import Literal

Channel = Literal["email", "sms", "push"]


@dataclass
class ValidationResult:
    """Результат валидации шаблона."""
    is_valid: bool
    errors: list[str]
    warnings: list[str]


def validate_template(
    code: str,
    name: str,
    channel: str,
    subject: str | None,
    body: str,
    allowed_variables: list[str],
) -> ValidationResult:
    """Валидировать шаблон (синтаксис, переменные, рендер).
    
    Args:
        code: Код шаблона.
        name: Название шаблона.
        channel: Канал доставки (email, sms, push).
        subject: Тема шаблона (может быть None).
        body: Тело шаблона.
        allowed_variables: Список разрешённых переменных.
    
    Returns:
        ValidationResult с флагом is_valid, списком ошибок и предупреждений.
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
        errors.append(f"Invalid channel: {channel}. Must be one of: {', '.join(valid_channels)}")
    
    variable_pattern = r"\{\{\s*(\w+)\s*\}\}"
    body_variables = set(re.findall(variable_pattern, body))
    subject_variables = set(re.findall(variable_pattern, subject or ""))
    all_used_variables = body_variables | subject_variables
    
    allowed_set = set(allowed_variables)
    for var in all_used_variables:
        if var not in allowed_set:
            errors.append(f"Variable '{var}' is used in template but not in allowed_variables")
    
    for var in allowed_variables:
        if var not in all_used_variables:
            warnings.append(f"Variable '{var}' is in allowed_variables but not used in template")
    
    open_count_body = len(re.findall(r"\{\{", body))
    close_count_body = len(re.findall(r"\}\}", body))
    if open_count_body != close_count_body:
        errors.append("Unclosed variable tag in body. Use {{ variable_name }} syntax")
    
    if subject:
        open_count_subject = len(re.findall(r"\{\{", subject))
        close_count_subject = len(re.findall(r"\}\}", subject))
        if open_count_subject != close_count_subject:
            errors.append("Unclosed variable tag in subject. Use {{ variable_name }} syntax")
    
    is_valid = len(errors) == 0
    
    return ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
    )
