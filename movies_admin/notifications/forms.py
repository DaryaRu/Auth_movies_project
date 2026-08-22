"""Формы для админ-панели уведомлений."""

import json
import uuid
from datetime import timezone

from django import forms
from django.utils.translation import gettext_lazy as _

from .api_client import (
    APIError,
    DuplicateError,
    MailingTemplateNotFoundError,
    MailingValidationError,
    TemplateNotFoundError,
    api_client,
)
from .models import NotificationTemplate


class NotificationTemplateForm(forms.Form):
    """Форма для шаблона уведомления (работает через API).
    
    Примечание: Поле code доступно только для создания шаблона.
    При редактировании существующего шаблона code недоступно для изменения,
    так как сервис нотификаций не поддерживает изменение кода шаблона.
    """

    class Meta:
        fields = '__all__'
        labels: dict[str, str] = {}
        model = None

    code = forms.CharField(
        label=_('Code'),
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'vTextField', 'maxlength': 255}),
        help_text=_('Уникальный код шаблона (например: review_liked). Изменение кода невозможно.')
    )
    name = forms.CharField(
        label=_('Name'),
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'vTextField', 'maxlength': 255})
    )
    channel = forms.ChoiceField(
        label=_('Channel'),
        choices=[('email', _('Email')), ('sms', _('SMS')), ('push', _('Push'))],
        widget=forms.RadioSelect()
    )
    subject = forms.CharField(
        label=_('Subject'),
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={'class': 'vTextField', 'maxlength': 500}),
        help_text=_('Тема сообщения. Поддерживает переменные в виде {{movie_title}}.')
    )
    body = forms.CharField(
        label=_('Body'),
        widget=forms.Textarea(attrs={'class': 'vLargeTextField', 'rows': 10}),
        help_text=_('Содержимое сообщения. Поддерживает переменные в виде {{movie_title}}.')
    )
    allowed_variables = forms.CharField(
        label=_('Allowed Variables'),
        required=False,
        widget=forms.Textarea(attrs={'class': 'vLargeTextField', 'rows': 3}),
        help_text=_('Список разрешённых переменных через запятую (например: user_name, movie_title)')
    )
    is_active = forms.BooleanField(
        label=_('Is Active'),
        required=False,
        widget=forms.CheckboxInput()
    )

    def __init__(self, *args, **kwargs):
        """Инициализация формы с данными из API."""
        api_data = kwargs.pop('api_data', None)

        kwargs.pop('instance', None)
        
        self._api_data = api_data
        
        if api_data and not any(k in kwargs for k in ('data', 'files')):
            initial_data = {
                'code': api_data.get('code', ''),
                'name': api_data.get('name', ''),
                'channel': api_data.get('channel', 'email'),
                'subject': api_data.get('subject', ''),
                'body': api_data.get('body', ''),
                'is_active': api_data.get('is_active', True),
            }
            allowed_vars = api_data.get('allowed_variables', [])
            if isinstance(allowed_vars, list):
                initial_data['allowed_variables'] = ', '.join(allowed_vars)
            else:
                initial_data['allowed_variables'] = str(allowed_vars) if allowed_vars else ''
            
            if 'initial' in kwargs:
                kwargs['initial'] = {**initial_data, **kwargs['initial']}
            else:
                kwargs['initial'] = initial_data
        
        super().__init__(*args, **kwargs)

    @property
    def instance(self):
        """Возвращает объект модели для совместимости с Django admin.
        
        Django admin ожидает form.instance для доступа к объекту модели.
        Это свойство игнорируется для формы NotificationTemplateForm,
        так как данные хранятся во внешнем сервисе, а не в БД.
        """
        if self._api_data and self._api_data.get('code'):
            obj, _ = NotificationTemplate.objects.get_or_create(
                code=self._api_data['code'],
                defaults={
                    'name': self._api_data.get('name', ''),
                    'channel': self._api_data.get('channel', 'email'),
                    'subject': self._api_data.get('subject') or '',
                    'body': self._api_data.get('body', ''),
                    'allowed_variables': self._api_data.get('allowed_variables', []),
                    'is_active': self._api_data.get('is_active', True),
                }
            )
            return obj
        return NotificationTemplate()

    def clean_allowed_variables(self):
        """Преобразовать строку переменных в список."""
        value = self.cleaned_data.get('allowed_variables', '')
        if value:
            variables = [v.strip() for v in value.split(',') if v.strip()]
            return variables
        return []

    def save_template(self, template_id: str | None = None, auth_token: str | None = None) -> dict:
        """Сохранить шаблон через API.

        Args:
            template_id: UUID шаблона для обновления (или None для создания).
            auth_token: JWT токен пользователя из auth-сервиса.
        
        Примечание: При обновлении шаблона (template_id указан) поле code НЕ отправляется,
        так как сервис нотификаций не поддерживает изменение кода шаблона.
        """
        data = {
            'name': self.cleaned_data['name'],
            'channel': self.cleaned_data['channel'],
            'subject': self.cleaned_data['subject'] or None,
            'body': self.cleaned_data['body'],
            'allowed_variables': self.cleaned_data['allowed_variables'],
            'is_active': self.cleaned_data['is_active'],
        }
        
        if template_id is None:
            data['code'] = self.cleaned_data['code']

        if template_id:
            try:
                return api_client.update_template(template_id, data, auth_token)
            except TemplateNotFoundError as exc:
                raise forms.ValidationError(_('Template not found in service')) from exc
            except APIError as e:
                raise forms.ValidationError(str(e)) from e
        else:
            try:
                return api_client.create_template(data, auth_token)
            except DuplicateError as exc:
                raise forms.ValidationError(_('Template with this code already exists')) from exc
            except APIError as e:
                raise forms.ValidationError(str(e)) from e


class JSONPayloadMixin:
    """Миксин для валидации JSON-поля payload_json."""

    def clean_payload_json(self):
        """Валидировать JSON."""
        value = self.cleaned_data.get('payload_json', '{}')
        if not value:
            return {}
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise forms.ValidationError(_('Invalid JSON: ') + str(e)) from e


class TemplatePreviewForm(JSONPayloadMixin, forms.Form):
    """Форма для предпросмотра шаблона с переменными."""
    class Meta:
        fields = '__all__'
        labels: dict[str, str] = {}
        model = None

    payload_json = forms.CharField(
        label=_('Test Payload (JSON)'),
        widget=forms.Textarea(attrs={'class': 'vLargeTextField', 'rows': 5}),
        required=False,
        help_text=_('JSON с тестовыми данными для подстановки в шаблон')
    )


class AdminMailingForm(JSONPayloadMixin, forms.Form):
    """Форма создания рассылки."""

    template = forms.ModelChoiceField(
        label=_('Template'),
        queryset=NotificationTemplate.objects.filter(is_active=True, channel='email'),
        widget=forms.Select(attrs={'class': 'vTextField'}),
        help_text=_('Выберите шаблон для рассылки')
    )
    audience_type = forms.ChoiceField(
        label=_('Audience'),
        choices=[
            ('all', _('All users')),
            ('subscription', _('By subscription level')),
        ],
        widget=forms.RadioSelect(),
        initial='all'
    )
    subscription_level = forms.IntegerField(
        label=_('Min subscription level'),
        min_value=1,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'vTextField', 'min': 1}),
        help_text=_('Минимальный уровень подписки (для фильтра "По уровню подписки")')
    )
    payload_json = forms.CharField(
        label=_('Payload (JSON)'),
        widget=forms.Textarea(attrs={'class': 'vLargeTextField', 'rows': 5}),
        required=False,
        help_text=_('Дополнительные данные для подстановки в шаблон (JSON). '
                    'Допустимые ключи — allowed_variables выбранного шаблона.')
    )
    scheduled_at = forms.DateTimeField(
        label=_('Scheduled at'),
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        help_text=_('Когда отправить. Пусто = отправить сразу.')
    )

    def clean(self):
        """Кросс-валидация: subscription_level обязателен при audience_type=subscription."""
        cleaned = super().clean()
        if cleaned.get('audience_type') == 'subscription' and not cleaned.get('subscription_level'):
            self.add_error('subscription_level', _('Required when audience type is "subscription"'))
        return cleaned

    def build_api_data(self, created_by: str) -> dict:
        """Собрать dict для API."""
        audience_filter = {}
        if self.cleaned_data['audience_type'] == 'subscription':
            audience_filter['subscription_level'] = {
                'gte': self.cleaned_data['subscription_level']
            }

        scheduled_at = self.cleaned_data.get('scheduled_at')
        if scheduled_at:
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
            scheduled_at = scheduled_at.isoformat()

        return {
            'template_id': str(self.cleaned_data['template'].id),
            'audience_filter': audience_filter,
            'payload': self.cleaned_data['payload_json'],
            'scheduled_at': scheduled_at,
            'created_by': created_by,
        }

    def save_mailing(self, auth_token: str | None = None, created_by: str | None = None) -> dict:
        """Создать рассылку через API."""
        data = self.build_api_data(created_by or str(uuid.uuid4()))
        try:
            return api_client.create_mailing(data, auth_token)
        except MailingValidationError as e:
            raise forms.ValidationError(str(e)) from e
        except MailingTemplateNotFoundError as e:
            raise forms.ValidationError(str(e)) from e
        except APIError as e:
            raise forms.ValidationError(str(e)) from e
