from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Notification, RecurringSchedule


class NotificationForm(forms.ModelForm):
    """Форма для создания/редактирования уведомления."""

    class Meta:
        model = Notification
        fields = '__all__'
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'vTextField', 'maxlength': 500}),
            'content': forms.Textarea(attrs={'class': 'vLargeTextField', 'rows': 10}),
            'delivery_channels': forms.CheckboxSelectMultiple(),
            'send_type': forms.RadioSelect(),
            'recipient_type': forms.RadioSelect(),
            'status': forms.RadioSelect(),
        }

    def clean(self):
        cleaned_data = super().clean()
        send_type = cleaned_data.get('send_type')
        scheduled_at = cleaned_data.get('scheduled_at')
        status = cleaned_data.get('status')

        # Проверка scheduled_at для отложенных уведомлений
        if send_type == Notification.SendType.SCHEDULED:
            if not scheduled_at:
                raise forms.ValidationError(
                    _('Для отложенной отправки необходимо указать дату и время')
                )
            if scheduled_at < timezone.now():
                raise forms.ValidationError(
                    _('Дата отправки должна быть в будущем')
                )

        # Проверка scheduled_at для повторяющихся уведомлений
        if send_type == Notification.SendType.RECURRING:
            if not scheduled_at:
                raise forms.ValidationError(
                    _('Для повторяющейся отправки необходимо указать дату и время')
                )

        # Автоматическая установка статуса при отправке
        if status == Notification.Status.DRAFT and send_type == Notification.SendType.IMMEDIATE:
            # Если immediate, статус остаётся draft до отправки
            pass

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance


class RecurringScheduleForm(forms.ModelForm):
    """Форма для расписания повторяющихся уведомлений."""

    class Meta:
        model = RecurringSchedule
        fields = '__all__'
        widgets = {
            'interval_type': forms.RadioSelect(),
        }

    def clean(self):
        cleaned_data = super().clean()
        interval_type = cleaned_data.get('interval_type')
        day_of_week = cleaned_data.get('day_of_week')
        day_of_month = cleaned_data.get('day_of_month')
        month = cleaned_data.get('month')

        # Валидация полей в зависимости от типа интервала
        if interval_type == RecurringSchedule.IntervalType.WEEKLY and not day_of_week:
            raise forms.ValidationError(
                _('Для еженедельной рассылки необходимо указать день недели')
            )

        if interval_type == RecurringSchedule.IntervalType.MONTHLY and not day_of_month:
            raise forms.ValidationError(
                _('Для ежемесячной рассылки необходимо указать день месяца')
            )

        if interval_type == RecurringSchedule.IntervalType.YEARLY:
            if not day_of_month:
                raise forms.ValidationError(
                    _('Для ежегодной рассылки необходимо указать день месяца')
                )
            if not month:
                raise forms.ValidationError(
                    _('Для ежегодной рассылки необходимо указать месяц')
                )

        return cleaned_data