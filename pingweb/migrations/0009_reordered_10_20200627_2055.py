# Generated by Django 3.0.5 on 2020-06-27 20:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pingweb', '0009_auto_20200627_1455'),
    ]

    operations = [
        migrations.AlterField(
            model_name='probegroup',
            name='name',
            field=models.CharField(max_length=128),
        ),
    ]
