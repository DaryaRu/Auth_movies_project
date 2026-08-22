"""Админ-панель для шаблонов уведомлений с интеграцией API сервиса нотификаций."""

import json
import logging
import uuid
from datetime import datetime, timezone

from django.contrib import admin, messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from .api_client import (
    APIError,
    MailingNotFoundError,
    TemplateNotFoundError,
    TemplatePreviewError,
    api_client,
)
from .forms import (
    AdminMailingForm,
    NotificationTemplateForm,
    TemplatePreviewForm,
)
from .models import AdminMailing, NotificationTemplate, ShortLinkSettings
from .short_link_admin import ShortLinkSettingsAdmin


def get_auth_token(request) -> str | None:
    """Получить JWT токен из сессии пользователя.

    Токен сохраняется в сессии после аутентификации через auth-сервис.
    """
    return request.session.get('jwt_token') or request.session.get('access_token')


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """Админ-панель для шаблонов уведомлений (интеграция с API сервиса)."""

    list_display = ('name', 'channel', 'is_active', 'code_display', 'created', 'modified')
    list_filter = ('is_active', 'channel')
    search_fields = ('name', 'code', 'subject', 'body')
    change_list_template = 'admin/notifications/template_changelist.html'
    change_form_template = 'admin/notifications/change_form.html'

    @admin.display(description=_('Code'))
    def code_display(self, obj):
        """Отображение кода шаблона."""
        return obj.code or '-'

    def get_urls(self):
        """Добавляем URL для предпросмотра и работы с API."""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<uuid:pk>/preview/',
                self.admin_site.admin_view(self.preview_template),
                name='notifications_notificationtemplate_preview',
            ),
            path(
                '<uuid:pk>/change/api/',
                self.admin_site.admin_view(self.change_view_api),
                name='notifications_notificationtemplate_change_api',
            ),
            path(
                'add/api/',
                self.admin_site.admin_view(self.add_view_api),
                name='notifications_notificationtemplate_add_api',
            ),
        ]
        return custom_urls + urls

    def add_view(self, request, form_url='', extra_context=None):
        """Перенаправляем на API view для создания шаблона."""
        return self.add_view_api(request)

    def add_view_api(self, request):
        """Обработка создания шаблона через API.
        
        Примечание: После создания шаблона обновляем локальную запись с датой modified из API.
        """
        logger = logging.getLogger(__name__)

        if request.method == 'POST':
            form = NotificationTemplateForm(request.POST)
            if form.is_valid():
                try:
                    auth_token = get_auth_token(request)
                    form.save_template(auth_token=auth_token)
                    self.message_user(request, _('Template created successfully'), messages.SUCCESS)
                    
                    template_code = form.cleaned_data['code']
                    try:
                        templates = api_client.list_templates(auth_token)
                        created_template = None
                        for t in templates:
                            if t.get('code') == template_code:
                                created_template = t
                                break
                        
                        if created_template:
                            template_uuid = created_template.get('template_id')
                            if template_uuid:
                                try:
                                    template_uuid = uuid.UUID(str(template_uuid))
                                except (ValueError, TypeError):
                                    template_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, template_code)
                            else:
                                template_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, template_code)
                            
                            modified_date = created_template.get('updated_at')
                            created_date = created_template.get('created_at')
                            
                            NotificationTemplate.objects.update_or_create(
                                code=template_code,
                                defaults={
                                    'id': template_uuid,
                                    'name': created_template.get('name', ''),
                                    'channel': created_template.get('channel', 'email'),
                                    'subject': created_template.get('subject') or '',
                                    'body': created_template.get('body', ''),
                                    'allowed_variables': created_template.get('allowed_variables', []),
                                    'is_active': created_template.get('is_active', True),
                                    'modified': modified_date,
                                    'created': created_date,
                                }
                            )
                    except (TemplateNotFoundError, APIError) as e:
                        logger.warning(f"Could not fetch created template from API: {e}")
                    
                    return HttpResponseRedirect(reverse('admin:notifications_notificationtemplate_changelist'))
                except Exception as e:
                    self.message_user(request, str(e), messages.ERROR)
        else:
            form = NotificationTemplateForm()

        context = {
            'title': _('Add Notification Template'),
            'form': form,
            'opts': self.model._meta,
            **self.admin_site.each_context(request),
        }
        return TemplateResponse(request, 'admin/notifications/template_form.html', context)

    def preview_template(self, request, pk):
        """Предпросмотр шаблона — рендер через notifications-service (тем же
        движком, что и реальная отправка у воркера)."""
        logger = logging.getLogger(__name__)
        
        template = None
        preview_data = None
        error_message = None
        form = TemplatePreviewForm()
        form_valid = False

        auth_token = get_auth_token(request)

        try:
            template = api_client.get_template(str(pk), auth_token)
            logger.info("Template data: %s", template)
        except (TemplateNotFoundError, APIError) as e:
            error_message = str(e)
            logger.error("Error getting template: %s", e)

        if request.method == 'POST':
            form = TemplatePreviewForm(request.POST)
            if form.is_valid():
                form_valid = True
                try:
                    payload = form.cleaned_data.get('payload_json', {})
                    if not payload:
                        payload = {}
                    logger.info(f"Rendering template with payload: {payload}")

                    render_result = api_client.preview_template(
                        str(pk), payload, auth_token
                    )
                    preview_data = {
                        'subject': render_result.get('subject'),
                        'body': render_result.get('body'),
                        'is_original': False,
                    }
                    logger.info(f"Rendered preview_data: {preview_data}")
                except (TemplateNotFoundError, TemplatePreviewError, APIError) as e:
                    error_message = str(e)
                    logger.error(f"Error rendering template: {e}")
                    preview_data = None
            else:
                logger.warning(f"Form is not valid: {form.errors}")
                preview_data = None
        elif template:

            preview_data = {
                'subject': template.get('subject', ''),
                'body': template.get('body', ''),
                'is_original': True,
            }
            logger.info("GET request, using original template data")

        context = {
            'template': template,
            'title': _('Preview Template'),
            'form': form,
            'preview_data': preview_data,
            'error_message': error_message,
            'variables': template.get('allowed_variables', []) if template else [],
            'form_valid': form_valid,
            **self.admin_site.each_context(request),
        }
        return TemplateResponse(request, 'admin/notifications/preview_template.html', context)

    def get_queryset(self, request):
        """Получить список шаблонов из API сервиса нотификаций.
        
        Поскольку реальные данные хранятся в сервисе нотификаций,
        а не в локальной БД, получаем их через API.
        
        Примечание: При синхронизации с API поле modified НЕ обновляется,
        чтобы не менять дату изменения шаблона без реального редактирования.
        """
        auth_token = get_auth_token(request)
        try:
            api_templates = api_client.list_templates(auth_token)
        except APIError:
            return super().get_queryset(request).none()
        
        base_manager = self.model._base_manager
        
        with transaction.atomic():
            existing_codes = set(
                base_manager.values_list('code', flat=True)
            )
            
            api_codes = set()
            for template_data in api_templates:
                api_codes.add(template_data.get('code', ''))
                
                template_uuid = template_data.get('template_id')
                if template_uuid:
                    try:
                        template_uuid = uuid.UUID(str(template_uuid))
                    except (ValueError, TypeError):
                        template_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, template_data.get('code', ''))
                else:
                    template_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, template_data.get('code', ''))
                
                existing = base_manager.filter(code=template_data.get('code')).first()
                
                if existing:
                    base_manager.filter(code=template_data.get('code')).update(
                        id=template_uuid,
                        name=template_data.get('name', ''),
                        channel=template_data.get('channel', 'email'),
                        subject=template_data.get('subject') or '',
                        body=template_data.get('body', ''),
                        allowed_variables=template_data.get('allowed_variables', []),
                        is_active=template_data.get('is_active', True),
                    )
                else:
                    base_manager.create(
                        id=template_uuid,
                        code=template_data.get('code', ''),
                        name=template_data.get('name', ''),
                        channel=template_data.get('channel', 'email'),
                        subject=template_data.get('subject') or '',
                        body=template_data.get('body', ''),
                        allowed_variables=template_data.get('allowed_variables', []),
                        is_active=template_data.get('is_active', True),
                    )
            
            codes_to_delete = existing_codes - api_codes
            if codes_to_delete:
                base_manager.filter(code__in=codes_to_delete).delete()
        
        return super().get_queryset(request)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Переопределяем change_view для загрузки данных из API и обработки сохранения.
        
        При GET запросе - загружаем данные из API для отображения формы.
        При POST запросе - обрабатываем сохранение через API (PATCH запрос).
        
        Примечание: Поле code делается readonly при редактировании, так как
        сервис нотификаций не поддерживает изменение кода шаблона.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        auth_token = get_auth_token(request)
        template_data = None
        try:
            template_data = api_client.get_template(str(object_id), auth_token)
            logger.info(f"Template data from API: {template_data}")
        except (TemplateNotFoundError, APIError) as e:
            logger.error(f"Error getting template: {e}")
            template_data = None
        
        if template_data:
            request.session['api_template_data'] = template_data
            request.session['current_template_data'] = template_data
        else:
            request.session.pop('api_template_data', None)
            request.session.pop('current_template_data', None)
        
        extra = extra_context or {}
        if template_data:
            extra['template_api_data'] = template_data
        
        if request.method == 'POST':
            return self.change_view_api(request, object_id, form_url, extra)
        
        if template_data:
            initial_data = {
                'code': template_data.get('code', ''),
                'name': template_data.get('name', ''),
                'channel': template_data.get('channel', 'email'),
                'subject': template_data.get('subject') or '',
                'body': template_data.get('body', ''),
                'is_active': template_data.get('is_active', True),
            }
            allowed_vars = template_data.get('allowed_variables', [])
            if isinstance(allowed_vars, list):
                initial_data['allowed_variables'] = ', '.join(allowed_vars)
            else:
                initial_data['allowed_variables'] = str(allowed_vars) if allowed_vars else ''
            
            logger.info(f"Initial data for form: {initial_data}")
            
            form = NotificationTemplateForm(
                initial=initial_data,
                api_data=template_data
            )

            form.fields['code'].widget.attrs['readonly'] = True
            form.fields['code'].help_text = _('Code cannot be changed. Unique code of the template.')
            
            logger.info(f"Form fields after init: code={form['code'].value()}, name={form['name'].value()}")
        else:
            form = NotificationTemplateForm()
        
        try:
            original = self.get_object(request, object_id)
        except Exception:
            original = None
        
        context = {
            'title': _('Change %s') % self.model._meta.verbose_name,
            'original': original,
            'form': form,
            'opts': self.model._meta,
            'template_api_data': extra.get('template_api_data'),
            **self.admin_site.each_context(request),
        }
        
        return TemplateResponse(request, self.change_form_template, context)

    def change_view_api(self, request, pk, form_url='', extra_context=None):
        """Обработка изменения шаблона через API.
        
        При POST запросе:
        - Валидируем форму
        - Отправляем PATCH запрос на API сервиса уведомлений
        - При успехе - обновляем локальную копию с датой из API
        - Редирект на страницу редактирования для отображения обновлённых данных
        
        Примечание: Дата modified обновляется только из ответа API,
        а не автоматически при сохранении в БД. Если API не вернул дату,
        используем текущее время.
        """
        if request.method == 'POST':
            api_data = request.session.get('api_template_data')
            if api_data:
                form = NotificationTemplateForm(request.POST, api_data=api_data)
            else:
                form = NotificationTemplateForm(request.POST)
            
            if form.is_valid():
                try:
                    auth_token = get_auth_token(request)
                    form.save_template(template_id=str(pk), auth_token=auth_token)
                    self.message_user(request, _('Template updated successfully'), messages.SUCCESS)
                    
                    fresh_template_data = None
                    try:
                        fresh_template_data = api_client.get_template(str(pk), auth_token)
                        if fresh_template_data:
                            request.session['api_template_data'] = fresh_template_data
                            request.session['current_template_data'] = fresh_template_data
                            
                            modified_date = fresh_template_data.get('updated_at')
                            if not modified_date:

                                modified_date = datetime.now(timezone.utc)
                            
                            NotificationTemplate.objects.filter(code=fresh_template_data.get('code')).update(
                                name=fresh_template_data.get('name', ''),
                                channel=fresh_template_data.get('channel', 'email'),
                                subject=fresh_template_data.get('subject') or '',
                                body=fresh_template_data.get('body', ''),
                                allowed_variables=fresh_template_data.get('allowed_variables', []),
                                is_active=fresh_template_data.get('is_active', True),
                                modified=modified_date,
                            )
                    except (TemplateNotFoundError, APIError):
                        pass
                    
                    return HttpResponseRedirect(reverse('admin:notifications_notificationtemplate_changelist'))
                except Exception as e:
                    self.message_user(request, str(e), messages.ERROR)
            else:
                self.message_user(request, _('Please correct the errors below'), messages.ERROR)
        
        return self.change_view(request, str(pk), form_url, extra_context)


@admin.register(AdminMailing)
class AdminMailingAdmin(admin.ModelAdmin):
    """Админ-панель для ручных рассылок (интеграция с API сервиса)."""

    list_display = ('id', 'template_name', 'status', 'scheduled_at', 'sent_at', 'created_at')
    list_filter = ('status',)
    search_fields = ('id',)
    change_list_template = 'admin/notifications/mailing_changelist.html'
    readonly_fields = ('template_id', 'audience_filter', 'payload', 'status',
                       'scheduled_at', 'sent_at', 'created_by', 'created_at')

    @admin.display(description=_('Template'))
    def template_name(self, obj):
        """Отображение названия шаблона."""
        template = NotificationTemplate.objects.filter(id=obj.template_id).first()
        return template.name if template else str(obj.template_id)

    def get_urls(self):
        """Кастомные URL для рассылок."""
        urls = super().get_urls()
        custom_urls = [
            path(
                'add/api/',
                self.admin_site.admin_view(self.add_view_api),
                name='notifications_adminmailing_add_api',
            ),
        ]
        return custom_urls + urls

    def add_view(self, request, form_url='', extra_context=None):
        """Перенаправляем на API view для создания рассылки."""
        return self.add_view_api(request)

    def add_view_api(self, request):
        """Обработка создания рассылки через API."""
        logger = logging.getLogger(__name__)

        if request.method == 'POST':
            form = AdminMailingForm(request.POST)
            if form.is_valid():
                try:
                    auth_token = get_auth_token(request)
                    created_by = str(request.user.id) if hasattr(request.user, 'id') else str(uuid.uuid4())
                    mailings = form.save_mailing(auth_token=auth_token, created_by=created_by)

                    if len(mailings) > 1:
                        self.message_user(
                            request,
                            _('Mailing split into %(count)d timezone buckets') % {'count': len(mailings)},
                            messages.SUCCESS,
                        )
                    else:
                        self.message_user(request, _('Mailing created successfully'), messages.SUCCESS)

                    for mailing in mailings:
                        self._sync_mailing(mailing)

                    return HttpResponseRedirect(
                        reverse('admin:notifications_adminmailing_changelist')
                    )
                except Exception as e:
                    logger.error(f"Error creating mailing: {e}")
                    self.message_user(request, str(e), messages.ERROR)
        else:
            form = AdminMailingForm()

        # Собираем данные шаблонов для отображения в форме
        template_data = {}
        for t in form.fields['template'].queryset:
            template_data[str(t.id)] = {
                'name': t.name,
                'subject': t.subject or '',
                'body': t.body or '',
                'allowed_variables': t.allowed_variables or [],
            }

        context = {
            'title': _('Add Mailing'),
            'form': form,
            'opts': self.model._meta,
            'template_data_json': json.dumps(template_data, ensure_ascii=False),
            **self.admin_site.each_context(request),
        }
        return TemplateResponse(request, 'admin/notifications/mailing_form.html', context)

    def get_queryset(self, request):
        """Синхронизация рассылок из API (аналогично шаблонам)."""
        auth_token = get_auth_token(request)
        try:
            api_mailings = api_client.list_mailings(auth_token)
        except APIError:
            return super().get_queryset(request).none()

        base_manager = self.model._base_manager

        with transaction.atomic():
            existing_ids = set(base_manager.values_list('id', flat=True))
            api_ids = set()

            for m in api_mailings:
                mailing_id = m.get('admin_mailing_id')
                if not mailing_id:
                    continue
                try:
                    api_ids.add(uuid.UUID(str(mailing_id)))
                except (ValueError, TypeError):
                    continue
                self._sync_mailing(m)

            to_delete = existing_ids - api_ids
            if to_delete:
                base_manager.filter(id__in=to_delete).delete()

        return super().get_queryset(request)

    def _sync_mailing(self, mailing_data: dict):
        """Синхронизировать одну рассылку из API-ответа."""
        try:
            mailing_id = uuid.UUID(str(mailing_data.get('admin_mailing_id', '')))
        except (ValueError, TypeError):
            return

        try:
            template_id = uuid.UUID(str(mailing_data.get('template_id', '')))
        except (ValueError, TypeError):
            template_id = uuid.uuid4()

        try:
            created_by = uuid.UUID(str(mailing_data.get('created_by', '')))
        except (ValueError, TypeError):
            created_by = uuid.uuid4()

        AdminMailing.objects.update_or_create(
            id=mailing_id,
            defaults={
                'template_id': template_id,
                'audience_filter': mailing_data.get('audience_filter', {}),
                'payload': mailing_data.get('payload', {}),
                'status': mailing_data.get('status', 'sending'),
                'scheduled_at': mailing_data.get('scheduled_at'),
                'sent_at': mailing_data.get('sent_at'),
                'created_by': created_by,
            }
        )

    def has_change_permission(self, request, obj=None):
        """Рассылка неизменяема."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Рассылка не удаляется."""
        return False

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Readonly-страница рассылки."""
        auth_token = get_auth_token(request)
        mailing = None
        error_message = None

        try:
            mailing = api_client.get_mailing(str(object_id), auth_token)
        except (MailingNotFoundError, APIError) as e:
            error_message = str(e)

        context = {
            'title': _('Mailing details'),
            'mailing': mailing,
            'error_message': error_message,
            'object_id': object_id,
            'opts': self.model._meta,
            **self.admin_site.each_context(request),
        }
        return TemplateResponse(
            request, 'admin/notifications/mailing_change_form.html', context
        )


@admin.register(ShortLinkSettings)
class ShortLinkSettingsAdminView(ShortLinkSettingsAdmin):
    """Регистрация настроек коротких ссылок в Django admin."""

    pass
