import uuid

from django.core.validators import MinValueValidator, MaxValueValidator
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
