"""
Test graphing functions
"""

import graphing
import time
import server
import database_mysql


def test1():
    points = [(1400, 100), (1401, 101), (1402, 100), (1403, 102)]
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
    figure.show()


if __name__ == '__main__':
    test2()
