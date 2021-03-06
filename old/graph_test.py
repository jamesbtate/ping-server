"""
Test graphing functions
"""

import matplotlib
if matplotlib.get_backend() != 'agg':
    matplotlib.use('TkAgg')
import graphing
import time
import server
import database_mysql


def test1():
    # points = [(1400, 100), (1401, 101), (1402, 100), (1403, 102)]
    times = [1400, 1401, 1402, 1403]
    values = [100, 101, 100, 102]
    figure = graphing.ping_figure(times, values)
    figure.show()


def test2():
    config = server.read_config()['server']
    db = database_mysql.DatabaseMysql(config)
    data = db.get_poll_data_by_pair(1)
    times = [_['time'] for _ in data]
    values = [_['latency'] for _ in data]
    figure = graphing.ping_figure(times, values)
    return figure


def test2a():
    test2()
    matplotlib.pyplot.show()


def test3():
    figure = test2()
    b64_src = graphing.figure_to_base64(figure)


def test4():
    config = server.read_config()['server']
    db = database_mysql.DatabaseMysql(config)
    data = db.get_poll_data_by_pair(40)
    success_times = []
    success_values = []
    timeout_times = []
    for datum in data:
        if datum['latency'] is None:
            timeout_times.append(datum['time'])
        else:
            success_times.append(datum['time'])
            success_values.append(datum['latency'] * 1000)
    return success_times, success_values, timeout_times


if __name__ == '__main__':
    test3()
