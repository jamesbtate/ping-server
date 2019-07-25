#!/usr/bin/env python3
"""
Webserver for this application...
"""

from database_mysql import DatabaseMysql
from database_binary import DatabaseBinary
from server import read_config
import graphing
import argparse
import logging
import misc
import time
import os

from flask import Flask, request, render_template, send_from_directory
app = Flask(__name__)
db = None


@app.route("/hello")
def hello():
    return "Hello World!"


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico')


@app.route("/")
def index():
    pairs = db.get_src_dst_pairs()
    for pair in pairs:
        try:
            pair['mtime'] = db.get_file_modification_time(pair['binary_file'],
                                                          iso8601=True)
        except FileNotFoundError:
            pair['mtime'] = "File not found"
        except PermissionError:
            pair['mtime'] = "Permission denied"
    for pair in pairs:
        # pair['polls'] = [_['count'] for _ in poll_counts if
        #                 _['src_dst'] == pair['id']][0]
        pair['polls'] = -7
    data = {
        'src_dst_pairs': pairs
    }
    return render_template("index.html", **data)


@app.route("/graph/<int:pair_id>")
def graph(pair_id):
    pair = db.get_src_dst_by_id(pair_id)
    start_time, stop_time = misc.get_time_extents(request.args)
    t = time.time()
    records = db.get_poll_data_by_id(pair_id, start=start_time, end=stop_time,
                                     convert_to_datetime=True)
    statistics = db.calculate_statistics(records)
    retrieve_time = time.time() - t
    t = time.time()
    base64_src = graphing.make_graph(pair, records)
    draw_time = time.time() - t
    data = {
        'pair_id': pair_id,
        'start_time': start_time,
        'stop_time': stop_time,
        'graph_src': base64_src,
        'retrieve_time': retrieve_time,
        'draw_time': draw_time,
        'statistics': statistics
    }
    return render_template("graph.html", **data)


def parse_args():
    description = "Run development webserver for ping project"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-d', '--debug', action='store_true',
                        help="Enable debug-level logging")
    args = parser.parse_args()
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if args.debug:
        logger.setLevel(logging.DEBUG)


def main():
    global app
    global db
    parse_args()
    db_params = read_config()['server']
    db = DatabaseBinary(db_params)
    app.run(debug=True, host='0.0.0.0')


if __name__ == '__main__':
    main()
