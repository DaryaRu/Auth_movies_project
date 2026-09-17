from django.db import migrations, models


def blank_phone_to_null(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(phone="").update(phone=None)


def null_phone_to_blank(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(phone__isnull=True).update(phone="")


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="phone",
            field=models.CharField(
                blank=True, max_length=20, null=True, verbose_name="phone"
            ),
        ),
        migrations.RunPython(blank_phone_to_null, null_phone_to_blank),
    ]
