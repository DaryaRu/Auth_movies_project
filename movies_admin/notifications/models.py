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
        ('email', _('Email')),
        ('sms', _('SMS')),
        ('push', _('Push')),
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


class AdminMailing(models.Model):
    """Ручная рассылка из админки.

    Примечание: Прокси-модель. Реальные данные хранятся в сервисе
    нотификаций и получаются через API.
    """

    id = models.UUIDField(_('id'), primary_key=True, default=uuid.uuid4, editable=False)
    template_id = models.UUIDField(_('template id'))
    audience_filter = models.JSONField(_('audience filter'), default=dict)
    payload = models.JSONField(_('payload'), default=dict)
    status = models.CharField(_('status'), max_length=20, choices=[
        ('scheduled', _('Scheduled')),
        ('sending', _('Sending')),
        ('sent', _('Sent')),
        ('failed', _('Failed')),
    ])
    scheduled_at = models.DateTimeField(_('scheduled at'), null=True, blank=True)
    sent_at = models.DateTimeField(_('sent at'), null=True, blank=True)
    created_by = models.UUIDField(_('created by'))
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        db_table = "content\".\"admin_mailing"
        verbose_name = _('admin mailing')
        verbose_name_plural = _('admin mailings')
        ordering = ['-created_at']

    def __str__(self):
        return f"{_('Mailing')} {self.id} ({self.get_status_display()})"


class ShortLinkSettings(models.Model):
    """Прокси-модель для регистрации в Django admin.

    Реальные данные хранятся в БД short_links сервиса.
    """

    class Meta:
        managed = False
        db_table = "content\".\"short_link_settings_proxy"
        verbose_name = _('short link settings')
        verbose_name_plural = _('short link settings')

    def __str__(self):
        return _('Short Link Settings')


