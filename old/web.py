#!/usr/bin/python3
"""
A webserver for serving the GUI.
Can be executed directly to get the development server or used as a
WSGI application.
"""

import mysql.connector
import configparser
# import logging
import flask


app = flask.Flask(__name__)
parser = configparser.ConfigParser(allow_no_value=True)
parser.read('ping.conf')


def _db_connection():
    db_params = parser['server']
    connection = mysql.connector.connect(user=db_params['db_user'],
                                         password=db_params['db_pass'],
                                         host=db_params['db_host'],
                                         database=db_params['db_db'])
    return connection


def _db_query(query, params=None, connection=None):
    if not connection:
        connection = _db_connection()
    cursor = connection.cursor()
    cursor.execute(query, params)
    return cursor.fetchall()


@app.route('/hello')
def hello():
    return "Hello, World!"


@app.route('/pairs')
def pairs():
    query = "SELECT id,CAST(INET_NTOA(src) as CHAR(20))," \
            + "CAST(INET_NTOA(dst) as CHAR(20)) FROM src_dst"
    data = _db_query(query)
    return flask.render_template('pairs.html', pairs=data)


if __name__ == '__main__':
    # log_format = '%(asctime)s %(levelname)s:%(module)s:%(funcName)s ' \
    #               + '%(message)s'
    # logging.basicConfig(format=log_format, level=logging.INFO)
    pass
