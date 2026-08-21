"""Миграция: модель AdminMailing для рассылок."""

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminMailing',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='id')),
                ('template_id', models.UUIDField(verbose_name='template id')),
                ('audience_filter', models.JSONField(default=dict, verbose_name='audience filter')),
                ('payload', models.JSONField(default=dict, verbose_name='payload')),
                ('status', models.CharField(choices=[('scheduled', 'Scheduled'), ('sending', 'Sending'), ('sent', 'Sent'), ('failed', 'Failed')], max_length=20, verbose_name='status')),
                ('scheduled_at', models.DateTimeField(blank=True, null=True, verbose_name='scheduled at')),
                ('sent_at', models.DateTimeField(blank=True, null=True, verbose_name='sent at')),
                ('created_by', models.UUIDField(verbose_name='created by')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
            ],
            options={
                'db_table': 'content"."admin_mailing',
                'verbose_name': 'admin mailing',
                'verbose_name_plural': 'admin mailings',
                'ordering': ['-created_at'],
            },
        ),
    ]