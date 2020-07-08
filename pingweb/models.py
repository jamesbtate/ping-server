from django.forms import ModelForm, TextInput, CheckboxSelectMultiple
from django.db import models
from enum import IntEnum
from typing import List


class Prober(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True, null=True)
    key = models.CharField(max_length=255)
    added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} ({self.id})'

    def get_absolute_url(self):
        return f"/configure/prober/{self.id}"

    class Meta:
        db_table = 'prober'

    def get_unique_targets(self):
        targets = set()
        for group in self.probegroup_set.all():
            targets.update(group.targets.all())
        return targets


class ProberForm(ModelForm):
    class Meta:
        model = Prober
        # fields = ['name', 'description', 'key']
        exclude = ['added']
        widgets = {
            'description': TextInput(attrs={'size': 42}),
        }


class Target(models.Model):

    class TargetType(models.TextChoices):
        ICMP = 'icmp', 'ICMP'

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, null=True)
    ip = models.GenericIPAddressField(protocol='IPv4', verbose_name="IP Address")
    type = models.CharField(max_length=4, choices=TargetType.choices,
                            default=TargetType.ICMP)
    port = models.PositiveIntegerField(blank=True, null=True)
    added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} - {self.ip} ({self.id})'

    def get_absolute_url(self):
        return f"/configure/target/{self.id}"

    class Meta:
        db_table = 'prober_target'


class TargetForm(ModelForm):
    class Meta:
        model = Target
        # fields = ['name', 'description', 'ip']
        exclude = []
        widgets = {
            'description': TextInput(attrs={'size': 42}),
        }


class ProbeGroup(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, null=True)
    probers = models.ManyToManyField(Prober, blank=True)
    targets = models.ManyToManyField(Target, blank=True)
    added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} ({self.id})'

    def get_absolute_url(self):
        return f"/configure/probe_group/{self.id}"


class ProbeGroupNewForm(ModelForm):
    class Meta:
        model = ProbeGroup
        # fields = ['name', 'description']
        exclude = []
        widgets = {
            'description': TextInput(attrs={'size': 42}),
            'probers': CheckboxSelectMultiple,
            'targets': CheckboxSelectMultiple,
        }


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
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - ({self.id})"


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
    read = models.BooleanField(default=False)

    @classmethod
    def get_unread_messages(cls) -> List['CollectorMessage']:
        """ Get a list of messages that have not been retrieved

        Marks the returned messages as retrieved.

        :return: a list of CollectorMessages or an empty list
        """
        messages = CollectorMessage.objects.filter(read=False)
        messages_list = list(messages)  # this must happen before the update
        messages.update(read=True)
        return messages_list


class Version(models.Model):
    ping_schema = models.BigIntegerField(primary_key=True)

    class Meta:
        managed = False
        db_table = 'version'
