import uuid

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('movies', '0002_filmwork_subscription_level'),
    ]

    operations = [
        migrations.CreateModel(
            name='Episode',
            fields=[
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('season_number', models.PositiveIntegerField(help_text='Season number (starting from 1)', verbose_name='season number')),
                ('episode_number', models.PositiveIntegerField(help_text='Episode number within the season (starting from 1)', verbose_name='episode number')),
                ('title', models.CharField(help_text='Title of this episode', max_length=255, verbose_name='episode title')),
                ('description', models.TextField(blank=True, help_text='Description/synopsis of this episode', verbose_name='episode description')),
                ('release_date', models.DateField(blank=True, help_text='Official release date of this episode', null=True, verbose_name='release date')),
                ('duration', models.PositiveIntegerField(blank=True, help_text='Episode duration in minutes', null=True, verbose_name='duration in minutes')),
                ('rating', models.FloatField(blank=True, help_text='Rating for this episode (0-10)', null=True, validators=[django.core.validators.MinValueValidator(0, message='The value cannot be less than 0'), django.core.validators.MaxValueValidator(10, message='The value cannot be greater than 10')], verbose_name='episode rating')),
                ('file_path', models.FileField(blank=True, help_text='Path to the video file for this episode', null=True, upload_to='episodes/', verbose_name='episode file path')),
                ('release_status', models.CharField(choices=[('planned', 'Planned'), ('in_production', 'In production'), ('released', 'Released'), ('archived', 'Archived')], default='planned', help_text='Current release status of this episode', max_length=20, verbose_name='release status')),
                ('is_premium', models.BooleanField(default=False, help_text='Is this episode available only for premium subscribers?', verbose_name='premium episode')),
                ('subscription_level', models.IntegerField(default=0, help_text='Minimum subscription level required to watch. 0 — available to everyone.', validators=[django.core.validators.MinValueValidator(0)], verbose_name='subscription level')),
                ('tv_show', models.ForeignKey(help_text='The TV show this episode belongs to', limit_choices_to={'type': 'tv_show'}, on_delete=django.db.models.deletion.CASCADE, related_name='episodes', to='movies.filmwork', verbose_name='TV show')),
                ('genres', models.ManyToManyField(help_text='Genres for this episode', related_name='episode_genres', to='movies.genre', verbose_name='genres')),
                ('persons', models.ManyToManyField(help_text='People involved in this episode', related_name='episode_persons', to='movies.person', verbose_name='persons')),
            ],
            options={
                'verbose_name': 'episode',
                'verbose_name_plural': 'episodes',
                'db_table': 'content"."episode',
                'ordering': ['tv_show', 'season_number', 'episode_number'],
            },
        ),
        migrations.AddConstraint(
            model_name='episode',
            constraint=models.UniqueConstraint(fields=('tv_show', 'season_number', 'episode_number'), name='unique_episode_in_season'),
        ),
        migrations.AddIndex(
            model_name='episode',
            index=models.Index(fields=['tv_show', 'season_number', 'episode_number'], name='episode_season_episode_idx'),
        ),
        migrations.AddIndex(
            model_name='episode',
            index=models.Index(fields=['release_date'], name='episode_release_date_idx'),
        ),
        migrations.AddIndex(
            model_name='episode',
            index=models.Index(fields=['release_status'], name='episode_release_status_idx'),
        ),
    ]