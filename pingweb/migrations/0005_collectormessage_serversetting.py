# Generated by Django 3.0.5 on 2020-05-30 02:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pingweb', '0004_auto_20200418_1908'),
    ]

    operations = [
        migrations.CreateModel(
            name='CollectorMessage',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('message', models.IntegerField(choices=[(1, 'ReloadSettings'), (2, 'NotifyProbers')])),
                ('posted', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='ServerSetting',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('value', models.CharField(max_length=255)),
            ],
        ),
    ]
