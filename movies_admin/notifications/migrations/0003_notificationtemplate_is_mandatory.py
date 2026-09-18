"""Миграция: поле is_mandatory у NotificationTemplate (обязательное
сообщение безопасности — доставляется независимо от настроек рассылок)."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_admin_mailing'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationtemplate',
            name='is_mandatory',
            field=models.BooleanField(default=False, verbose_name='is mandatory'),
        ),
    ]
