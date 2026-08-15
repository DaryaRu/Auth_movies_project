"""Рендеринг шаблонов уведомлений."""

from dataclasses import dataclass


@dataclass
class RenderResult:
    """Результат рендеринга шаблона."""
    rendered_subject: str | None
    rendered_body: str


def render_template(
    subject: str | None,
    body: str,
    payload: dict | None = None,
) -> RenderResult:
    """Отрендерить шаблон с подстановкой переменных.
    
    Args:
        subject: Тема шаблона (может быть None).
        body: Тело шаблона.
        payload: Данные для подстановки в шаблон.
    
    Returns:
        RenderResult с отрендеренными subject и body.
    """
    if payload is None:
        payload = {}
    
    rendered_subject = subject
    rendered_body = body
    
    for key, value in payload.items():
        str_value = str(value)
        if rendered_subject is not None:
            rendered_subject = rendered_subject.replace(f"{{{{ {key} }}}}", str_value)
            rendered_subject = rendered_subject.replace(f"{{{{{key}}}}}", str_value)
        
        rendered_body = rendered_body.replace(f"{{{{ {key} }}}}", str_value)
        rendered_body = rendered_body.replace(f"{{{{{key}}}}}", str_value)
    
    return RenderResult(
        rendered_subject=rendered_subject,
        rendered_body=rendered_body,
    )
