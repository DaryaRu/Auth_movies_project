import logging
import uuid

import requests
from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _
from notifications.api_client import APIError, api_client

from movies.models import (
    Episode,
    FilmWork,
    Genre,
    GenreFilmWork,
    Person,
    PersonFilmWork,
)

logger = logging.getLogger(__name__)

NEW_EPISODE_TEMPLATE_CODE = 'new_episode'
NEW_EPISODE_NOTIFICATION_TYPE = 'new_episode'


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


class EpisodeForm(ModelForm):
    class Meta:
        model = Episode
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_new_episode = not self.instance.pk
        self._tv_show_genre_ids = []
        self._tv_show_person_ids = []
        if self._is_new_episode and self.instance.tv_show_id:
            try:
                tv_show = FilmWork.objects.get(pk=self.instance.tv_show_id)
                self.fields['genres'].initial = list(tv_show.genres.values_list('pk', flat=True))

                self._tv_show_genre_ids = list(tv_show.genres.values_list('pk', flat=True))
                self._tv_show_person_ids = list(tv_show.persons.values_list('pk', flat=True))
            except FilmWork.DoesNotExist:
                pass
        elif self.instance.pk:
            pass

    def save(self, commit=True):
        """При создании нового эпизода автоматически копируем жанры и персон из TV шоу."""
        instance = super().save(commit=False)

        if commit:
            instance.save()
            self.save_m2m()

            if self._is_new_episode and self._tv_show_genre_ids:
                form_genres = self.cleaned_data.get('genres', [])
                form_genre_ids = list(form_genres.values_list('pk', flat=True)) if form_genres else []
                all_genre_ids = list(set(self._tv_show_genre_ids) | set(form_genre_ids))
                instance.genres.set(all_genre_ids)

            if self._is_new_episode and self._tv_show_person_ids:
                form_persons = self.cleaned_data.get('persons', [])
                form_person_ids = list(form_persons.values_list('pk', flat=True)) if form_persons else []
                all_person_ids = list(set(self._tv_show_person_ids) | set(form_person_ids))
                instance.persons.set(all_person_ids)

        return instance

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

    def clean_genres(self):
        """Валидация жанров - возвращаем выбранные жанры."""
        return self.cleaned_data.get('genres', [])

    def clean_persons(self):
        """Валидация персон - возвращаем выбранные персоны."""
        return self.cleaned_data.get('persons', [])


class EpisodeReleaseStatusFilter(admin.SimpleListFilter):
    """Фильтр по статусу релиза эпизода."""
    title = _('release status')
    parameter_name = 'release_status'

    def lookups(self, request, model_admin):
        return Episode.ReleaseStatus.choices

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(release_status=value)
        return queryset


class EpisodeSeasonFilter(admin.SimpleListFilter):
    """Фильтр по номеру сезона."""
    title = _('season')
    parameter_name = 'season_number'

    def lookups(self, request, model_admin):
        seasons = Episode.objects.values_list('season_number', flat=True).distinct().order_by('season_number')
        return [(str(season), f'Season {season}') for season in seasons]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(season_number=int(value))
        return queryset


class PersonEpisodeInline(admin.TabularInline):
    model = PersonFilmWork
    extra = 1
    autocomplete_fields = ('person',)
    fk_name = 'film_work'


class GenreEpisodeInline(admin.TabularInline):
    model = GenreFilmWork
    extra = 1
    autocomplete_fields = ('genre',)
    fk_name = 'film_work'


@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    form = EpisodeForm
    list_display = (
        'title',
        'tv_show',
        'episode_code_display',
        'release_date',
        'release_status',
        'rating',
        'subscription_level',
    )
    list_filter = (
        'tv_show',
        EpisodeSeasonFilter,
        EpisodeReleaseStatusFilter,
        'is_premium',
        'subscription_level',
    )
    search_fields = ('title', 'tv_show__title', 'description')
    search_help_text = _("Search by episode title, TV show title or description")
    autocomplete_fields = ('tv_show',)
    filter_horizontal = ('genres', 'persons')
    list_per_page = 50
    preserve_filters = True
    save_on_top = True
    date_hierarchy = 'release_date'
    fieldsets = (
        (None, {
            'fields': ('tv_show', 'season_number', 'episode_number', 'title', 'description')
        }),
        (_('Release info'), {
            'fields': ('release_date', 'duration', 'release_status')
        }),
        (_('Rating & Subscription'), {
            'fields': ('rating', 'is_premium', 'subscription_level')
        }),
        (_('Genres & Persons'), {
            'fields': ('genres', 'persons'),
            'description': _('Genres and persons are inherited from the TV show. '
                           'You can add additional genres and persons to this episode.')
        }),
        (_('File'), {
            'fields': ('file_path',)
        }),
    )

    def episode_code_display(self, obj):
        return obj.episode_code
    episode_code_display.short_description = _('Episode Code')  # type: ignore[attr-defined]
    episode_code_display.admin_order_field = 'season_number'  # type: ignore[attr-defined]

    def save_model(self, request, obj, form, change):
        old_status = form.initial.get('release_status') if change else None
        super().save_model(request, obj, form, change)
        if (
            obj.release_status == Episode.ReleaseStatus.RELEASED
            and old_status != Episode.ReleaseStatus.RELEASED
        ):
            self._notify_new_episode(request, obj)

    def _notify_new_episode(self, request, episode):
        """Публикует триггер уведомления о новой серии (Scheduled group)."""
        try:
            template = api_client.get_template_by_code(NEW_EPISODE_TEMPLATE_CODE)
            api_client.upsert_notification_trigger(
                content_id=str(episode.tv_show_id),
                notification_type=NEW_EPISODE_NOTIFICATION_TYPE,
                template_id=template['template_id'],
                payload={
                    'tv_show_title': episode.tv_show.title,
                    'season_number': episode.season_number,
                    'episode_number': episode.episode_number,
                    'episode_title': episode.title,
                },
            )
        except APIError as e:
            logger.warning(
                "Failed to publish new_episode trigger for episode %s: %s",
                episode.pk,
                e,
            )
            messages.warning(
                request,
                _("Серия сохранена, но не удалось опубликовать уведомление: %(error)s")
                % {"error": e},
            )


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

    get_genres.short_description = _('Genres')  # type: ignore[attr-defined]

    def get_autocomplete_fields(self, request):
        return super().get_autocomplete_fields(request)
