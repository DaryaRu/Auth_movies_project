import logging
import uuid

import requests
from django.conf import settings
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from movies.models import (
    FilmWork,
    Genre,
    GenreFilmWork,
    Person,
    PersonFilmWork,
)

logger = logging.getLogger(__name__)


def _get_max_subscription_level() -> int | None:
    """Запрашивает максимальный уровень подписки из auth-сервиса."""
    url = settings.AUTH_API_SUBSCRIPTION_LEVELS_URL
    if not url:
        return None
    try:
        headers = {"X-Request-Id": str(uuid.uuid4())}
        response = requests.get(url, timeout=3, headers=headers)
        if response.status_code == 200:
            levels = response.json()
            return max(levels) if levels else None
    except Exception as e:
        logger.warning("Не удалось получить уровни подписок: %s", e)
    return None


class FilmWorkForm(ModelForm):
    class Meta:
        model = FilmWork
        fields = '__all__'

    def clean_subscription_level(self):
        value = self.cleaned_data['subscription_level']
        if value < 0:
            raise ValidationError('Уровень подписки не может быть отрицательным.')
        max_level = _get_max_subscription_level()
        if max_level is not None and value > max_level:
            raise ValidationError(
                f'Уровень {value} недоступен. Сначала создайте подписку с этим уровнем в сервисе авторизации. '
                f'Доступные уровни: 0–{max_level}.'
            )
        return value


class RatingRangeFilter(admin.SimpleListFilter):
    title = _('rating')
    parameter_name = 'rating_range'

    def lookups(self, request, model_admin):
        return [
            ('0-5', '0–5'),
            ('5-7', '5–7'),
            ('7-10', '7–10'),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            start, end = map(int, value.split('-'))
            return queryset.filter(rating__gte=start, rating__lte=end)
        return queryset


class GenreFilmWorkInline(admin.TabularInline):
    model = GenreFilmWork
    extra = 1
    autocomplete_fields = ('genre',)


class PersonFilmWorkInline(admin.TabularInline):
    model = PersonFilmWork
    extra = 1
    autocomplete_fields = ('person',)


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    search_help_text = _("Search by name")
    list_per_page = 50
    preserve_filters = True
    save_on_top = True


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('full_name',)
    search_fields = ('full_name',)
    search_help_text = _("Search by full name")
    list_per_page = 50
    preserve_filters = True
    save_on_top = True


@admin.register(FilmWork)
class FilmWorkAdmin(admin.ModelAdmin):
    form = FilmWorkForm
    inlines = (GenreFilmWorkInline, PersonFilmWorkInline,)
    list_display = ('title', 'type', 'creation_date', 'rating', 'subscription_level', 'get_genres',)
    list_filter = ('type', 'genres', 'subscription_level', RatingRangeFilter)
    search_fields = ('title',)
    search_help_text = _("Search by title")
    list_prefetch_related = ('genres',)
    list_per_page = 50
    preserve_filters = True
    save_on_top = True

    def get_genres(self, obj):
        return ', '.join([genre.name for genre in obj.genres.all()])

    get_genres.short_description = _('Genres')

    def get_autocomplete_fields(self, request):
        return super().get_autocomplete_fields(request)
