#!/usr/bin/env python3
"""
Webserver for this application...
"""

from database_mysql import DatabaseMysql
from database_influxdb import DatabaseInfluxDB
from server import read_config
import graphing
import argparse
import logging
import misc
import time
import os
import gc

import misc

from flask import Flask, request, render_template, send_from_directory,\
                  jsonify, send_file
app = Flask(__name__)


@app.route("/hello")
def hello():
    return "Hello World!"


@app.route('/static/<filename>')
def static_file(filename):
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               filename)


@app.route('/favicon.ico')
def favicon():
    return static_file('favicon.ico')


@app.route("/")
def index():
    pairs = db.get_src_dst_pairs()
    for pair in pairs:
        prober_name = pair['prober_name']
        dst = pair['dst']
        dt = db.last_poll_time_by_pair(prober_name, dst)
        pair['mtime'] = dt.isoformat()
        pair['polls'] = db.get_poll_counts_by_pair(prober_name, dst)
    data = {
        'src_dst_pairs': pairs
    }
    return render_template("index.html", **data)


@app.route("/graph/<int:pair_id>")
def graph_page(pair_id):
    pair = db.get_src_dst_by_id(pair_id)
    start_time, stop_time = misc.get_time_extents(request.args)
    t = time.time()
    records = db.get_poll_data_by_id(pair_id, start=start_time, end=stop_time,
                                     convert_to_datetime=True)
    statistics = db.calculate_statistics(records)
    retrieve_time = time.time() - t
    data = {
        'pair_id': pair_id,
        'prober_name': pair['prober_name'],
        'dst': pair['dst'],
        'start_time': start_time,
        'stop_time': stop_time,
        'retrieve_time': retrieve_time,
        'statistics': statistics
    }
    return render_template("graph.html", **data)


@app.route("/graph_image/<int:pair_id>")
def graph_image(pair_id):
    pair = db.get_src_dst_by_id(pair_id)
    start_time, stop_time = misc.get_time_extents(request.args)
    records = db.get_poll_data_by_id(pair_id, start=start_time, end=stop_time,
                                     convert_to_datetime=True)
    t = time.time()
    kwargs = {}
    if request.args.get('success_rate'):
        kwargs['reduce'] = 60
        kwargs['success_rate'] = True
    bytes_io = graphing.make_graph_png(pair, records, **kwargs)
    bytes_io.seek(0)
    draw_time = time.time() - t
    return send_file(bytes_io, mimetype='image/png')


@app.route("/cache_info/get_poll_data")
def cache_info_get_poll_data():
    cache = db.cache
    return jsonify({
        'Entries': len(cache.keys()),
        'Records': cache.currsize,
        'Max Records': cache.maxsize
    })


@app.route("/gc")
def garbage_collect():
    gc.collect()
    return "Garbage collected"


@app.route("/about")
def about():
    return render_template("about.html")


def parse_args():
    description = "Run development webserver for ping project"
    parser = misc.make_generic_parser(description)
    args = parser.parse_args()
    return args


def main():
    global app
    global db
    args = parse_args()
    params = read_config(args.config_file)['server']
    db = DatabaseInfluxDB(params)
    app.run(debug=True, host=params['web_address'], port=params['web_port'])


if __name__ == '__main__':
    main()

