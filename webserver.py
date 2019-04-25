#!/usr/bin/python3
"""
Webserver for this application...
"""

from database_mysql import DatabaseMysql
from server import read_config

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


def main():
    global app
    global db
    db_params = read_config()['server']
    db = DatabaseMysql(db_params)
    app.run(debug=True)


if __name__ == '__main__':
    main()