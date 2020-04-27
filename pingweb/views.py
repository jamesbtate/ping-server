#!/usr/bin/env python3
"""
Django views for the pingweb application
"""

from django.shortcuts import render, redirect, reverse
from django.http import HttpRequest, HttpResponse, QueryDict
from urllib.parse import urlencode
import json
import time
import os
import gc

from pingweb.models import Prober, ProberForm
from pingweb.forms import GraphOptionsForm

from database_influxdb import DatabaseInfluxDB
import graphing
import config
import misc


from django.conf import settings
params = misc.read_config(settings.LEGACY_CONFIG_FILE)['server']
db = DatabaseInfluxDB(params)


def hello(request):
    return HttpResponse("Hello World!")


def test(request):
    return render(request, "test.html")


def index(request):
    pairs = db.get_src_dst_pairs()
    for pair in pairs:
        prober_name = pair.prober.name
        dst = pair.dst
        dt = db.last_poll_time_by_pair(prober_name, dst)
        pair.mtime = dt.isoformat()
        pair.polls = db.get_poll_counts_by_pair(prober_name, dst)
    data = {
        'src_dst_pairs': pairs
    }
    # flask: return render_template("index.html", **data)
    return render(request, 'index.html', data)


def graph_page(request, pair_id):
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
    records = db.get_poll_data_by_id(pair_id, start=start_time, end=stop_time,
                                     convert_to_datetime=True)
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
    }
    # flask: return render_template("graph.html", **data)
    return render(request, 'graph.html', data)


def graph_image(request, pair_id):
    pair = db.get_src_dst_by_id(pair_id)
    graph_options_form = GraphOptionsForm(request.GET)
    if graph_options_form.is_valid():
        start_time, stop_time = graph_options_form.get_time_extents()
    else:
        start_time, stop_time = misc.get_time_extents_from_params('1h')
    records = db.get_poll_data_by_id(pair_id, start=start_time, end=stop_time,
                                     convert_to_datetime=True)
    t = time.time()
    kwargs = {}
    if request.GET.get('success_rate'):
        kwargs['reduce'] = 60
        kwargs['success_rate'] = True
    bytes_io = graphing.make_graph_png(pair, records, **kwargs)
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


def configure_prober(request: HttpRequest):
    probers = Prober.objects.all()
    if request.method == 'POST':
        form = ProberForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(request.path_info)
    else:
        form = ProberForm()
    data = {'probers': probers, 'form': form}
    return render(request, 'configure_prober.html', data)
