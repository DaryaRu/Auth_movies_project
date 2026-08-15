"""Админ-панель для шаблонов уведомлений с интеграцией API сервиса нотификаций."""

import logging
import uuid
from datetime import datetime, timezone

from django.contrib import admin, messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from .api_client import APIError, TemplateNotFoundError, api_client
from .forms import NotificationTemplateForm, TemplatePreviewForm
from .models import NotificationTemplate
from .renderers import render_template
from .validators import validate_template


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
        """Добавляем URL для предпросмотра, валидации и работы с API."""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<uuid:pk>/preview/',
                self.admin_site.admin_view(self.preview_template),
                name='notifications_notificationtemplate_preview',
            ),
            path(
                '<uuid:pk>/validate/',
                self.admin_site.admin_view(self.validate_template),
                name='notifications_notificationtemplate_validate',
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
        """Предпросмотр шаблона с локальным рендерингом."""
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

                    render_result = render_template(
                        subject=template.get('subject') if template else '',
                        body=template.get('body', '') if template else '',
                        payload=payload,
                    )
                    preview_data = {
                        'subject': render_result.rendered_subject,
                        'body': render_result.rendered_body,
                        'is_original': False,
                    }
                    logger.info(f"Rendered preview_data: {preview_data}")
                except Exception as e:
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

    def validate_template(self, request, pk):
        """Валидация шаблона с локальной проверкой."""
        template = None
        validation_result = None
        error_message = None

        auth_token = get_auth_token(request)

        try:
            template = api_client.get_template(str(pk), auth_token)
            validation_result = validate_template(
                code=template.get('code', ''),
                name=template.get('name', ''),
                channel=template.get('channel', 'email'),
                subject=template.get('subject') or '',
                body=template.get('body', ''),
                allowed_variables=template.get('allowed_variables', []),
            )
        except (TemplateNotFoundError, APIError) as e:
            error_message = str(e)

        context = {
            'template': template,
            'title': _('Validate Template'),
            'validation_result': validation_result,
            'error_message': error_message,
            **self.admin_site.each_context(request),
        }
        return TemplateResponse(request, 'admin/notifications/validate_template.html', context)

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

    def get_form(self, request, obj=None, **kwargs):
        """Получить форму с данными из API.
        
        Переопределяем для передачи api_data в форму.
        """
        api_data = request.session.get('api_template_data')
        
        if api_data:
            class ApiDataForm(NotificationTemplateForm):
                def __init__(self, *args, **form_kwargs):
                    form_kwargs['api_data'] = api_data
                    super().__init__(*args, **form_kwargs)
            
            return ApiDataForm
        
        return NotificationTemplateForm

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
