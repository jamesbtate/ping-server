# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Prober(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    key = models.CharField(max_length=255)
    added = models.DateTimeField()

    class Meta:
        db_table = 'prober'


class ProberTarget(models.Model):
    id = models.BigAutoField(primary_key=True)
    prober = models.ForeignKey(Prober, models.DO_NOTHING)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    ip = models.PositiveIntegerField()
    type = models.CharField(max_length=4)
    port = models.PositiveIntegerField(blank=True, null=True)
    added = models.DateTimeField()

    class Meta:
        db_table = 'prober_target'


class SrcDst(models.Model):
    id = models.SmallAutoField(primary_key=True)
    prober = models.ForeignKey(Prober, models.DO_NOTHING)
    dst = models.GenericIPAddressField(protocol='IPv4')

    class Meta:
        db_table = 'src_dst'


class Version(models.Model):
    ping_schema = models.BigIntegerField(primary_key=True)

    class Meta:
        managed = False
        db_table = 'version'
