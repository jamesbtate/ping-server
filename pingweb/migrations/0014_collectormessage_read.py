# Generated by Django 3.0.5 on 2020-07-08 00:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pingweb', '0013_serversetting_updated'),
    ]

    operations = [
        migrations.AddField(
            model_name='collectormessage',
            name='read',
            field=models.BooleanField(default=False),
        ),
    ]
