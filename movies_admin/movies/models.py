import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class TimeStampedMixin(models.Model):
    created = models.DateTimeField(
        _('created'),
        auto_now_add=True
    )
    modified = models.DateTimeField(
        _('modified'),
        auto_now=True
    )

    class Meta:
        abstract = True


class UUIDMixin(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    class Meta:
        abstract = True


class Genre(UUIDMixin, TimeStampedMixin):
    name = models.CharField(
        _('name'),
        max_length=255
    )
    description = models.TextField(
        _('description'),
        blank=True
    )

    class Meta:
        db_table = "content\".\"genre"
        verbose_name = _('genre')
        verbose_name_plural = _('genres')

    def __str__(self):
        return self.name


class Person(UUIDMixin, TimeStampedMixin):
    full_name = models.CharField(
        _('full name'),
        max_length=255
    )

    class Meta:
        db_table = "content\".\"person"
        verbose_name = _('person')
        verbose_name_plural = _('persons')

    def __str__(self):
        return self.full_name


class FilmWork(UUIDMixin, TimeStampedMixin):

    class Type(models.TextChoices):
        MOVIE = 'movie', _('Movie')
        TV_SHOW = 'tv_show', _('TV show')

    title = models.CharField(
        _('title'),
        max_length=255,
    )
    description = models.TextField(
        _('description'),
        blank=True
    )
    creation_date = models.DateField(
        _('creation date'),
        blank=True,
        null=True,
    )
    file_path = models.FileField(
        _('file path'),
        upload_to='movies/',
        blank=True,
        null=True
    )
    rating = models.FloatField(
        _('rating'),
        validators=[
            MinValueValidator(
                0,
                message=_('The value cannot be less than 0')
            ),
            MaxValueValidator(
                10,
                message=_('The value cannot be greater than 10')
            )
        ],
        blank=True,
        null=True,
    )
    type = models.CharField(
        _('type'),
        max_length=10,
        choices=Type.choices
    )
    subscription_level = models.IntegerField(
        _('subscription level'),
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_('Minimum subscription level required to watch. 0 — available to everyone.'),
    )
    genres = models.ManyToManyField(
        Genre,
        through='GenreFilmWork',
        verbose_name=_('genres')
    )
    persons = models.ManyToManyField(
        Person,
        through='PersonFilmWork',
        verbose_name=_('persons')
    )

    class Meta:
        db_table = "content\".\"film_work"
        verbose_name = _('film work')
        verbose_name_plural = _('film works')
        indexes = [
            models.Index(
                fields=['title'],
                name='film_work_title_idx'
            ),
            models.Index(
                fields=['creation_date'],
                name='film_work_creation_date_idx'
            ),
            models.Index(
                fields=['rating'],
                name='film_work_rating_idx'
            ),
        ]

    def __str__(self):
        return self.title


class GenreFilmWork(UUIDMixin):
    film_work = models.ForeignKey(
        'FilmWork',
        on_delete=models.CASCADE,
        verbose_name=_('film work')
    )
    genre = models.ForeignKey(
        'Genre',
        on_delete=models.CASCADE,
        verbose_name=_('genre'),
        related_name='genre_film_work'
    )
    created = models.DateTimeField(
        _('created'),
        auto_now_add=True
    )

    class Meta:
        db_table = "content\".\"genre_film_work"
        constraints = [
            models.UniqueConstraint(
                fields=['genre', 'film_work'],
                name='film_work_genre_idx'
            )
        ]


class PersonFilmWork(UUIDMixin, TimeStampedMixin):

    class Role(models.TextChoices):
        ACTOR = 'actor', _('Actor')
        DIRECTOR = 'director', _('Director')
        WRITER = 'writer', _('Writer')

    film_work = models.ForeignKey(
        'FilmWork',
        on_delete=models.CASCADE,
        verbose_name=_('film work')
    )
    person = models.ForeignKey(
        'Person',
        on_delete=models.CASCADE,
        verbose_name=_('person'),
        related_name='person_film_work'
    )
    role = models.CharField(
        _('role'),
        max_length=20,
        choices=Role.choices
    )
    created = models.DateTimeField(
        _('created'),
        auto_now_add=True
    )

    class Meta:
        db_table = "content\".\"person_film_work"
        constraints = [
            models.UniqueConstraint(
                fields=['film_work', 'person', 'role'],
                name='film_work_person_idx'
            )
        ]


class Episode(UUIDMixin, TimeStampedMixin):
    """Модель эпизода сериала.

    Позволяет хранить информацию о каждом эпизоде сериала отдельно,
    что необходимо для уведомлений о выходе новых серий.
    """

    class ReleaseStatus(models.TextChoices):
        """Статус релиза эпизода."""
        PLANNED = 'planned', _('Planned')
        IN_PRODUCTION = 'in_production', _('In production')
        RELEASED = 'released', _('Released')
        ARCHIVED = 'archived', _('Archived')

    tv_show = models.ForeignKey(
        'FilmWork',
        on_delete=models.CASCADE,
        verbose_name=_('TV show'),
        related_name='episodes',
        limit_choices_to={'type': 'tv_show'},
        help_text=_('The TV show this episode belongs to')
    )
    season_number = models.PositiveIntegerField(
        _('season number'),
        help_text=_('Season number (starting from 1)')
    )
    episode_number = models.PositiveIntegerField(
        _('episode number'),
        help_text=_('Episode number within the season (starting from 1)')
    )
    title = models.CharField(
        _('episode title'),
        max_length=255,
        help_text=_('Title of this episode')
    )
    description = models.TextField(
        _('episode description'),
        blank=True,
        help_text=_('Description/synopsis of this episode')
    )
    release_date = models.DateField(
        _('release date'),
        blank=True,
        null=True,
        help_text=_('Official release date of this episode')
    )
    duration = models.PositiveIntegerField(
        _('duration in minutes'),
        blank=True,
        null=True,
        help_text=_('Episode duration in minutes')
    )
    rating = models.FloatField(
        _('episode rating'),
        validators=[
            MinValueValidator(
                0,
                message=_('The value cannot be less than 0')
            ),
            MaxValueValidator(
                10,
                message=_('The value cannot be greater than 10')
            )
        ],
        blank=True,
        null=True,
        help_text=_('Rating for this episode (0-10)')
    )
    file_path = models.FileField(
        _('episode file path'),
        upload_to='episodes/',
        blank=True,
        null=True,
        help_text=_('Path to the video file for this episode')
    )
    release_status = models.CharField(
        _('release status'),
        max_length=20,
        choices=ReleaseStatus.choices,
        default=ReleaseStatus.PLANNED,
        help_text=_('Current release status of this episode')
    )
    is_premium = models.BooleanField(
        _('premium episode'),
        default=False,
        help_text=_('Is this episode available only for premium subscribers?')
    )
    subscription_level = models.IntegerField(
        _('subscription level'),
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_('Minimum subscription level required to watch. 0 — available to everyone.'),
    )

    genres = models.ManyToManyField(
        Genre,
        verbose_name=_('genres'),
        related_name='episode_genres',
        help_text=_('Genres for this episode')
    )
    persons = models.ManyToManyField(
        Person,
        verbose_name=_('persons'),
        related_name='episode_persons',
        help_text=_('People involved in this episode')
    )

    class Meta:
        db_table = "content\".\"episode"
        verbose_name = _('episode')
        verbose_name_plural = _('episodes')
        ordering = ['tv_show', 'season_number', 'episode_number']
        constraints = [
            models.UniqueConstraint(
                fields=['tv_show', 'season_number', 'episode_number'],
                name='unique_episode_in_season'
            ),
        ]
        indexes = [
            models.Index(
                fields=['tv_show', 'season_number', 'episode_number'],
                name='episode_season_episode_idx'
            ),
            models.Index(
                fields=['release_date'],
                name='episode_release_date_idx'
            ),
            models.Index(
                fields=['release_status'],
                name='episode_release_status_idx'
            ),
        ]

    def __str__(self):
        return f'{self.tv_show.title} - S{self.season_number:02d}E{self.episode_number:02d}: {self.title}'

    @property
    def episode_code(self) -> str:
        """Возвращает код эпизода в формате S01E01."""
        return f'S{self.season_number:02d}E{self.episode_number:02d}'
