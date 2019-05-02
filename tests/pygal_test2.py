#!/usr/bin/python3
import mysql.connector
import configparser
import pygal


parser = configparser.ConfigParser(allow_no_value=True)
parser.read('../ping.conf')


def _db_connection():
    db_params = parser['server']
    connection = mysql.connector.connect(user=db_params['db_user'],
                                         password=db_params['db_pass'],
                                         host=db_params['db_host'],
                                         database=db_params['db_db'])
    return connection


connection = _db_connection()
cursor = connection.cursor()

query = "SELECT time,latency FROM output WHERE src_dst=37"
print("running query...")
cursor.execute(query, {})
print("fetching results...")
data = cursor.fetchall()
print("rows:", len(data))

line = pygal.DateTimeLine()
print("Making graph...")
line.add("blah", data)
print("Saving graph...")
line.render_to_png('line.png')
