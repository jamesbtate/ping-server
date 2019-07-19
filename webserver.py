#!/usr/bin/env python3
"""
Webserver for this application...
"""

from database_mysql import DatabaseMysql
from database_binary import DatabaseBinary
from server import read_config
import graphing
import misc
import time
import os

from flask import Flask, render_template, send_from_directory
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
    poll_counts = db.get_poll_counts_by_pair()
    for pair in pairs:
        #pair['polls'] = [_['count'] for _ in poll_counts if
        #                 _['src_dst'] == pair['id']][0]
        pair['polls'] = -7
    data = {
        'src_dst_pairs': pairs
    }
    return render_template("index.html", **data)


@app.route("/graph/<int:pair_id>")
def graph(pair_id):
    pair = db.get_src_dst_by_id(pair_id)
    title = str.format("Ping Results {} to {}", pair['src'], pair['dst'])
    t = time.time()
    data = db.get_poll_data_by_id(pair_id, convert_to_datetime=True)
    success_times = []
    success_values = []
    timeout_times = []
    for datum in data:
        if datum[1] is None:
            timeout_times.append(datum[0])
        else:
            success_times.append(datum[0])
            # multiply by 1000 for millis
            success_values.append(datum[1] * 1000)
    retrieve_time = time.time() - t
    t = time.time()
    figure = graphing.ping_figure(success_times, success_values, timeout_times,
                                  label=title, x_label="Time",
                                  y_label="Milliseconds")
    base64_src = graphing.figure_to_base64(figure)
    draw_time = time.time() - t
    data = {
        'points': len(data),
        'successes': len(success_times),
        'timeouts': len(timeout_times),
        'graph_src': base64_src,
        'retrieve_time': retrieve_time,
        'draw_time': draw_time
    }
    return render_template("graph.html", **data)


def main():
    global app
    global db
    db_params = read_config()['server']
    db = DatabaseBinary(db_params)
    app.run(debug=True, host='0.0.0.0')


if __name__ == '__main__':
    main()
