#!/usr/bin/env python3
"""
Django views for the pingweb application
"""

from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, QueryDict
from urllib.parse import urlencode
import json
import time
import gc

from pingweb.models import *
from pingweb.forms import GraphOptionsForm

from database_influxdb import DatabaseInfluxDB
import graphing
import misc
import env


params = env.get_influxdb_params()
db = DatabaseInfluxDB(params)


def hello(request):
    return HttpResponse("Hello World!")


def test(request):
    return render(request, "test.html")


def index(request):
    pairs = db.get_src_dst_pairs()
    error = ''
    try:
        for pair in pairs:
            prober_name = pair.prober.name
            dst = pair.dst
            dt = db.last_poll_time_by_pair(prober_name, dst)
            pair.mtime = dt.isoformat()
            pair.polls = db.get_poll_counts_by_pair(prober_name, dst)
    except Exception as e:
        error = 'Error talking to InfluxDB: ' + str(e)
    data = {
        'src_dst_pairs': pairs,
        'error': error
    }
    # flask: return render_template("index.html", **data)
    return render(request, 'index.html', data)


def graph_page(request, pair_id: int):
    error = ''
    pair = db.get_src_dst_by_id(pair_id)
    graph_options_form = GraphOptionsForm(request.GET)
    if graph_options_form.is_valid():
        start_time, stop_time = graph_options_form.get_time_extents()
    else:
        start_time, stop_time = misc.get_time_extents_from_params('1h')
    graph_options_form.set_datetime_fields(start_time, stop_time)
    graph_options_form.set_field_defaults()
    graph_image_url = '/graph_image/' + str(pair_id) + '?' + urlencode(request.GET.dict())
    t = time.time()
    records = []
    try:
        records = db.get_poll_data_by_id(pair_id, start=start_time, end=stop_time,
                                         convert_to_datetime=True)
    except Exception as e:
        error = 'Error talking to InfluxDB: ' + str(e)
    statistics = db.calculate_statistics(records)
    retrieve_time = time.time() - t
    success_rate = 0
    if statistics['echos'] > 0:
        success_rate = statistics['successes'] / statistics['echos'] * 100
    data = {
        'pair_id': pair_id,
        'prober_name': pair.prober.name,
        'dst': pair.dst,
        'start_time': start_time,
        'stop_time': stop_time,
        'retrieve_time': retrieve_time,
        'statistics': statistics,
        'minimum': statistics['minimum'] * 1000,
        'maximum': statistics['maximum'] * 1000,
        'average': statistics['mean'] * 1000,
        'success_rate': success_rate,
        'graph_options_form': graph_options_form,
        'graph_image_url': graph_image_url,
        'error': error,
    }
    # flask: return render_template("graph.html", **data)
    return render(request, 'graph.html', data)


def graph_image(request, pair_id: int):
    pair = db.get_src_dst_by_id(pair_id)
    graph_options_form = GraphOptionsForm(request.GET)
    if graph_options_form.is_valid():
        start_time, stop_time = graph_options_form.get_time_extents()
    else:
        data = {f: e.get_json_data() for f, e in graph_options_form.errors.items()}
        return HttpResponse(json.dumps(data))
    records = db.get_poll_data_by_id(pair_id, start=start_time, end=stop_time,
                                     convert_to_datetime=True)
    t = time.time()
    kwargs = {}
    bytes_io = graphing.make_graph_png(pair, records, **graph_options_form.cleaned_data)
    bytes_io.seek(0)
    # draw_time = time.time() - t
    # flask: return send_file(bytes_io, mimetype='image/png')
    return HttpResponse(bytes_io, content_type='image/png')


def about(request):
    # flask: return render_template("about.html")
    return render(request, 'about.html')


def cache_info_get_poll_data(request):
    cache = db.cache
    data = {
        'Entries': len(cache.keys()),
        'Records': cache.currsize,
        'Max Records': cache.maxsize
    }
    # flask: return jsonify(data)
    return HttpResponse(json.dumps(data))


def garbage_collect(request):
    gc.collect()
    return HttpResponse("Garbage collected")


def configure(request):
    return redirect('/configure/prober')


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


def edit_probe_group(request: HttpRequest, id:int):
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
