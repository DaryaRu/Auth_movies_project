from django import forms
from django.contrib import admin
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .forms import NotificationForm, RecurringScheduleForm
from .models import Notification, NotificationLog, NotificationTemplate, RecurringSchedule


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """Админ-панель для шаблонов уведомлений."""

    list_display = ('name', 'subject', 'is_active', 'created', 'modified')
    list_filter = ('is_active',)
    search_fields = ('name', 'subject', 'content')
    readonly_fields = ('created', 'modified', 'preview_button')
    fieldsets = (
        (None, {
            'fields': ('name', 'subject', 'content', 'is_active')
        }),
        (_('Dates'), {
            'fields': ('created', 'modified', 'preview_button'),
            'classes': ('collapse',)
        }),
    )

    def preview_button(self, obj):
        """Кнопка для предпросмотра шаблона."""
        if obj.pk:
            url = reverse('admin:notifications_notificationtemplate_preview', args=[obj.pk])
            return format_html(
                '<a href="{}" target="_blank" class="button">{}</a>',
                url,
                _('Preview Template')
            )
        return ''
    preview_button.short_description = _('Preview')

    def get_urls(self):
        """Добавляем URL для предпросмотра."""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<uuid:pk>/preview/',
                self.admin_site.admin_view(self.preview_template),
                name='notifications_notificationtemplate_preview',
            ),
        ]
        return custom_urls + urls

    def preview_template(self, request, pk):
        """Предпросмотр шаблона."""
        template = NotificationTemplate.objects.get(pk=pk)
        context = {
            'template': template,
            'title': _('Preview Template'),
            'subject_preview': template.subject,
            'content_preview': template.content,
            'variables': ['{{user_name}}', '{{email}}', '{{movie_title}}', '{{subscription_level}}'],
        }
        return TemplateResponse(request, 'admin/notifications/preview_template.html', context)


class RecurringScheduleInline(admin.StackedInline):
    """Inline для расписания повторяющихся уведомлений."""

    model = RecurringSchedule
    form = RecurringScheduleForm
    can_delete = False
    verbose_name = _('Recurring Schedule')
    verbose_name_plural = _('Recurring Schedule')
    extra = 0

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Показываем inline только если send_type=recurring
        if obj and obj.send_type != Notification.SendType.RECURRING:
            formset.extra = 0
            formset.max_num = 0
        return formset


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Админ-панель для уведомлений."""

    list_display = ('subject', 'recipient_type', 'send_type', 'status', 'created_by', 'created')
    list_filter = ('status', 'send_type', 'recipient_type', 'created_by', 'delivery_channels')
    search_fields = ('subject', 'content')
    readonly_fields = ('created', 'modified', 'sent_at', 'created_by')
    inlines = [RecurringScheduleInline]
    fieldsets = (
        (None, {
            'fields': ('template', 'subject', 'content')
        }),
        (_('Delivery'), {
            'fields': ('delivery_channels', 'recipient_type', 'subscription_level')
        }),
        (_('Schedule'), {
            'fields': ('send_type', 'scheduled_at')
        }),
        (_('Status'), {
            'fields': ('status',)
        }),
        (_('Dates'), {
            'fields': ('created', 'modified', 'sent_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        """Устанавливаем created_by при сохранении."""
        if not change:
            obj.created_by = request.user
        if obj.send_type == Notification.SendType.IMMEDIATE and obj.status == Notification.Status.DRAFT:
            obj.status = Notification.Status.PENDING
        super().save_model(request, obj, form, change)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    """Админ-панель для логов уведомлений (только чтение)."""

    list_display = ('notification', 'email', 'channel', 'status', 'sent_at')
    list_filter = ('status', 'channel', 'notification')
    search_fields = ('email', 'user_id', 'notification__subject')
    readonly_fields = (
        'id', 'notification', 'user_id', 'email', 'channel', 'status', 'sent_at', 'error_message'
    )
    fieldsets = (
        (None, {
            'fields': ('id', 'notification', 'user_id', 'email', 'channel')
        }),
        (_('Status'), {
            'fields': ('status', 'sent_at', 'error_message')
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True  # Разрешаем просмотр, но не редактирование

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(RecurringSchedule)