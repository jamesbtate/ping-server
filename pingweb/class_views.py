#!/usr/bin/env python3
"""
Django views for the pingweb application
"""

from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.http import HttpRequest, HttpResponse, QueryDict
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from urllib.parse import urlencode
import json
import time
import gc

from pingweb.models import *
from pingweb.forms import GraphOptionsForm

import misc
import env




def list_prober(request: HttpRequest):
    probers = Prober.objects.all()
    if request.method == 'POST':
        form = ProberForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(request.path_info)
    else:
        form = ProberForm()
    data = {'probers': probers, 'form': form}
    return render(request, 'list_prober.html', data)


def edit_prober(request: HttpRequest, id: int):
    prober = Prober.objects.get(id=id)
    if request.method == 'POST':
        form = ProberForm(request.POST, instance=prober)
        if form.is_valid():
            form.save()
            return redirect(request.path_info)
    else:
        form = ProberForm(instance=prober)
    data = {'prober': prober, 'form': form}
    return render(request, 'edit_prober.html', data)


class ProberDelete(DeleteView):
    model = Prober
    success_url = reverse_lazy('list_prober')


def list_target(request: HttpRequest):
    targets = ProberTarget.objects.all()
    if request.method == 'POST':
        form = TargetForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(request.path_info)
    else:
        form = TargetForm()
    data = {'targets': targets, 'form': form}
    return render(request, 'list_target.html', data)


def edit_target(request: HttpRequest, id: int):
    target = ProberTarget.objects.get(id=id)
    if request.method == 'POST':
        form = TargetForm(request.POST, instance=target)
        if form.is_valid():
            form.save()
            return redirect(request.path_info)
    else:
        form = TargetForm(instance=target)
    data = {'target': target, 'form': form}
    return render(request, 'edit_target.html', data)


class TargetDelete(DeleteView):
    model = ProberTarget
    success_url = reverse_lazy('list_target')


def list_probe_group(request: HttpRequest):
    probe_groups = ProbeGroup.objects.all()
    if request.method == 'POST':
        form = ProbeGroupNewForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(request.path_info)
    else:
        form = ProbeGroupNewForm()
    data = {'probe_groups': probe_groups, 'form': form}
    return render(request, 'list_probe_group.html', data)


def edit_probe_group(request: HttpRequest, id: int):
    probe_group = ProbeGroup.objects.get(id=id)
    if request.method == 'POST':
        form = ProbeGroupNewForm(request.POST, instance=probe_group)
        if form.is_valid():
            form.save()
            return redirect(request.path_info)
    else:
        form = ProbeGroupNewForm(instance=probe_group)
    data = {'probe_group': probe_group, 'form': form}
    return render(request, 'edit_probe_group.html', data)


class ProbeGroupDelete(DeleteView):
    model = ProbeGroup
    success_url = reverse_lazy('list_probe_group')
