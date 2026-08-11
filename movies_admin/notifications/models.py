import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from users.models import User


class TimeStampedMixin(models.Model):
    """Mixin с полями created и modified."""

    created = models.DateTimeField(_('created'), auto_now_add=True)
    modified = models.DateTimeField(_('modified'), auto_now=True)

    class Meta:
        abstract = True


class NotificationTemplate(TimeStampedMixin):
    """Шаблон уведомления."""

    name = models.CharField(_('name'), max_length=255)
    subject = models.CharField(
        _('subject'),
        max_length=500,
        help_text=_('Тема сообщения. Поддерживает переменные: {{user_name}}, {{movie_title}}, etc.')
    )
    content = models.TextField(
        _('content'),
        help_text=_('Содержимое сообщения. Поддерживает переменные: {{user_name}}, {{movie_title}}, etc.')
    )
    is_active = models.BooleanField(_('is active'), default=True)

    class Meta:
        db_table = "content\".\"notification_template"
        verbose_name = _('notification template')
        verbose_name_plural = _('notification templates')
        ordering = ['-created']

    def __str__(self):
        return self.name


class Notification(TimeStampedMixin):
    """Рассылка уведомлений."""

    class SendType(models.TextChoices):
        IMMEDIATE = 'immediate', _('Immediate')
        SCHEDULED = 'scheduled', _('Scheduled')
        RECURRING = 'recurring', _('Recurring')

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        PENDING = 'pending', _('Pending')
        SENT = 'sent', _('Sent')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')

    class RecipientType(models.TextChoices):
        ALL = 'all', _('All users')
        BY_SUBSCRIPTION = 'by_subscription', _('By subscription level')
        MANUAL = 'manual', _('Manual selection')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('template'),
        related_name='notifications'
    )
    subject = models.CharField(_('subject'), max_length=500)
    content = models.TextField(_('content'))
    delivery_channels = models.JSONField(
        _('delivery channels'),
        default=list,
        help_text=_('Список каналов доставки: ["email", "sms", "push"]')
    )
    recipient_type = models.CharField(
        _('recipient type'),
        max_length=20,
        choices=RecipientType.choices,
        default=RecipientType.ALL
    )
    subscription_level = models.IntegerField(
        _('subscription level'),
        default=0,
        help_text=_('Минимальный уровень подписки для получателей'),
        blank=True,
        null=True
    )
    send_type = models.CharField(
        _('send type'),
        max_length=20,
        choices=SendType.choices,
        default=SendType.IMMEDIATE
    )
    scheduled_at = models.DateTimeField(
        _('scheduled at'),
        null=True,
        blank=True,
        help_text=_('Дата и время отправки (для отложенных и повторяющихся)')
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('created by'),
        related_name='created_notifications'
    )
    sent_at = models.DateTimeField(_('sent at'), null=True, blank=True)

    class Meta:
        db_table = "content\".\"notification"
        verbose_name = _('notification')
        verbose_name_plural = _('notifications')
        ordering = ['-created']

    def __str__(self):
        return self.subject


class RecurringSchedule(TimeStampedMixin):
    """Расписание повторяющихся уведомлений."""

    class IntervalType(models.TextChoices):
        DAILY = 'daily', _('Daily')
        WEEKLY = 'weekly', _('Weekly')
        MONTHLY = 'monthly', _('Monthly')
        YEARLY = 'yearly', _('Yearly')

    notification = models.OneToOneField(
        Notification,
        on_delete=models.CASCADE,
        verbose_name=_('notification'),
        related_name='recurring_schedule'
    )
    interval_type = models.CharField(
        _('interval type'),
        max_length=20,
        choices=IntervalType.choices,
        default=IntervalType.WEEKLY
    )
    day_of_week = models.IntegerField(
        _('day of week'),
        null=True,
        blank=True,
        help_text=_('День недели (0-6, где 0=понедельник). Для weekly.'),
    )
    day_of_month = models.IntegerField(
        _('day of month'),
        null=True,
        blank=True,
        help_text=_('День месяца (1-31). Для monthly.'),
    )
    month = models.IntegerField(
        _('month'),
        null=True,
        blank=True,
        help_text=_('Месяц (1-12). Для yearly.'),
    )
    end_date = models.DateField(
        _('end date'),
        null=True,
        blank=True,
        help_text=_('Дата окончания повторений')
    )
    is_active = models.BooleanField(_('is active'), default=True)

    class Meta:
        db_table = "content\".\"recurring_schedule"
        verbose_name = _('recurring schedule')
        verbose_name_plural = _('recurring schedules')

    def __str__(self):
        return f'{self.get_interval_type_display()} - {self.notification.subject}'


class NotificationLog(TimeStampedMixin):
    """Лог отправки уведомлений."""

    class LogStatus(models.TextChoices):
        SENT = 'sent', _('Sent')
        FAILED = 'failed', _('Failed')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        verbose_name=_('notification'),
        related_name='logs'
    )
    user_id = models.UUIDField(_('user ID'), null=True, blank=True)
    email = models.EmailField(_('email'), blank=True)
    channel = models.CharField(_('channel'), max_length=20)
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=LogStatus.choices,
        default=LogStatus.SENT
    )
    sent_at = models.DateTimeField(_('sent at'), auto_now_add=True)
    error_message = models.TextField(_('error message'), blank=True)

    class Meta:
        db_table = "content\".\"notification_log"
        verbose_name = _('notification log')
        verbose_name_plural = _('notification logs')
        ordering = ['-sent_at']

    def __str__(self):
        return f'{self.notification.subject} -> {self.email or self.user_id} ({self.channel})'