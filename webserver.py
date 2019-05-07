#!/usr/bin/env python3
"""
Webserver for this application...
"""

from database_mysql import DatabaseMysql
from server import read_config
import graphing
import misc

from flask import Flask, render_template
app = Flask(__name__)
db = None


@app.route("/hello")
def hello():
    return "Hello World!"


@app.route("/")
def index():
    pairs = db.get_src_dst_pairs()
    poll_counts = db.get_poll_counts_by_pair()
    for pair in pairs:
        pair['polls'] = [_['count'] for _ in poll_counts if _['src_dst'] == pair['id']][0]
    data = {
        'src_dst_pairs': pairs
    }
    return render_template("index.html", **data)


@app.route("/graph/<int:pair_id>")
def graph(pair_id):
    pair = db.get_src_dst_by_id(pair_id)
    title = str.format("Ping Results {} to {}", pair['src'], pair['dst'])
    data = db.get_poll_data_by_pair(pair_id)
    success_times = []
    success_values = []
    timeout_times = []
    for datum in data:
        if datum['latency'] is None:
            timeout_times.append(datum['time'])
        else:
            success_times.append(datum['time'])
            success_values.append(datum['latency'] * 1000)
    # success_times = [_['time'] for _ in data]
    # success_values = [_['latency'] * 1000 if misc.is_number(_['latency'])
    #                   else None for _ in data]
    figure = graphing.ping_figure(success_times, success_values, timeout_times,
                                  label=title, x_label="Time",
                                  y_label="Milliseconds")
    base64_src = graphing.figure_to_base64(figure)
    data = {
        'points': len(data),
        'successes': len(success_times),
        'timeouts': len(timeout_times),
        'graph_src': base64_src
    }
    return render_template("graph.html", **data)


def main():
    global app
    global db
    db_params = read_config()['server']
    db = DatabaseMysql(db_params)
    app.run(debug=True, host='0.0.0.0')


if __name__ == '__main__':
    main()