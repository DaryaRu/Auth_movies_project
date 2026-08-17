"""Модели для приложения уведомлений.

Примечание: Модель NotificationTemplate используется только для отображения
в админ-панели. Реальные данные шаблонов хранятся в сервисе нотификаций
и получаются через API.
"""

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class NotificationTemplate(models.Model):
    """Шаблон уведомления.

    Примечание: Эта модель используется только для отображения в админ-панели.
    Реальные данные хранятся в сервисе нотификаций и получаются через API.
    """

    id = models.UUIDField(_('id'), primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('name'), max_length=255)
    code = models.CharField(_('code'), max_length=255, unique=True)
    channel = models.CharField(_('channel'), max_length=20, choices=[
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push'),
    ])
    subject = models.CharField(_('subject'), max_length=500, blank=True, null=True)
    body = models.TextField(_('body'))  # Основное поле, синхронизируемое с сервисом
    allowed_variables = models.JSONField(_('allowed variables'), default=list)
    is_active = models.BooleanField(_('is active'), default=True)
    created = models.DateTimeField(_('created'), auto_now_add=True)
    modified = models.DateTimeField(_('modified'), null=True, blank=True)

    class Meta:
        db_table = "content\".\"notification_template"
        verbose_name = _('notification template')
        verbose_name_plural = _('notification templates')
        ordering = ['-created']

    def __str__(self):
        return self.name