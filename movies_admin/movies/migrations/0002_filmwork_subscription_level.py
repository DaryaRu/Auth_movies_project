from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('movies', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='filmwork',
            name='subscription_level',
            field=models.IntegerField(
                default=0,
                validators=[MinValueValidator(0)],
                verbose_name='subscription level',
            ),
        ),
    ]
