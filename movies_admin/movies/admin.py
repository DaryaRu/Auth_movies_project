from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from movies.models import (
    FilmWork,
    Genre,
    GenreFilmWork,
    Person,
    PersonFilmWork
)


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
    inlines = (GenreFilmWorkInline, PersonFilmWorkInline,)
    list_display = ('title', 'type', 'creation_date', 'rating', 'get_genres',)
    list_filter = ('type', 'genres', RatingRangeFilter)
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
