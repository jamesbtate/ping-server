# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
from django.forms import ModelForm, TextInput
from enum import IntEnum


class Prober(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    key = models.CharField(max_length=255)
    added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'prober'


class ProberForm(ModelForm):
    class Meta:
        model = Prober
        fields = ['name', 'description', 'key']
        widgets = {
            'description': TextInput(attrs={'size': 42}),
        }


class ProberTarget(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    ip = models.GenericIPAddressField(protocol='IPv4', verbose_name="IP Address")
    type = models.CharField(max_length=4)
    port = models.PositiveIntegerField(blank=True, null=True)
    added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'prober_target'


class TargetForm(ModelForm):
    class Meta:
        model = ProberTarget
        fields = ['name', 'description', 'ip']
        widgets = {
            'description': TextInput(attrs={'size': 42}),
        }


class ProbeGroup(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    probers = models.ManyToManyField(Prober)
    targets = models.ManyToManyField(ProberTarget)
    added = models.DateTimeField(auto_now_add=True)


class SrcDst(models.Model):
    id = models.SmallAutoField(primary_key=True)
    prober = models.ForeignKey(Prober, models.DO_NOTHING)
    dst = models.GenericIPAddressField(protocol='IPv4')

    class Meta:
        db_table = 'src_dst'


class ServerSetting(models.Model):
    """ Settings for the collector daemon and the webserver. """
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)


class CollectorMessageType(IntEnum):
    ReloadSettings = 1
    NotifyProbers = 2

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]


class CollectorMessage(models.Model):
    """ Messages from the webserver to the collector """
    id = models.BigAutoField(primary_key=True)
    message = models.IntegerField(choices=CollectorMessageType.choices())
    posted = models.DateTimeField(auto_now_add=True)

    def type(self):
        return CollectorMessageType(self.message)


class Version(models.Model):
    ping_schema = models.BigIntegerField(primary_key=True)

    class Meta:
        managed = False
        db_table = 'version'
