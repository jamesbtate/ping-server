"""
Functions for generating graphs of the ping data
"""

from database_influxdb import TIMEOUT_VALUE
import matplotlib.dates
matplotlib.use('agg')  # this does nothing if matplotlib.pyplot is imported
import matplotlib.pyplot as plt
from typing import Tuple, List, Dict
import datetime
import base64
import io


locator = matplotlib.dates.AutoDateLocator()
formatter = matplotlib.dates.ConciseDateFormatter(locator)


def ping_figure(success_times, success_values, timeout_times,
                label="Ping Results", x_label=None, y_label=None)\
        -> Tuple[plt.Figure, plt.Subplot]:
    """ Plot ping results. No decimation.

    success_times - list of times (x-values on the graph).
    success_values - list of ping latencies (y-values on the graph).
    timeout_times - A list of times that had a timeout instead of a success.
    label - Optional title for the graph.
    x_label - Optional X-axis label for the graph.
    y_label - Option Y-axis label for the graph.

    Returns a figure from plt.subplots()
    """
    figure: plt.Figure
    axes: plt.Subplot
    figure, axes = plt.subplots()
    if success_times or timeout_times:
        axes.xaxis.set_major_locator(locator)
        axes.xaxis.set_major_formatter(formatter)
    axes.set_title(label)
    if x_label:
        axes.set_xlabel(x_label)
    if y_label:
        axes.set_ylabel(y_label)
    if success_times:
        axes.plot(success_times, success_values, linestyle='',
                  color='tab:blue', marker='.', label=label, markersize=2)
    y_min = min(success_values) if success_values else 0
    y_max = max(success_values) if success_values else 1000
    y_range = y_max - y_min
    y_bound = axes.get_ybound()
    axes.vlines(timeout_times, y_min - y_range, y_max + y_range,
                color='tab:red', linewidth=1)
    axes.set_ybound(y_bound)
    axes.tick_params(axis='x', labelrotation=30)
    return figure, axes


def round_to_int(num, base):
    """ Rounds a number 'num' to the nearest multiple of the integer 'base'.

    :param num: Number to round
    :param base: Round to a multiple of this integer
    :return: Integer
    """
    return base * round(num / base)


def reduce_data_points(records: List[Dict], bucket_duration: int) -> List[Dict]:
    """ Split data points into multiple buckets and calculate summary data for each bucket.

    :param records:
    :param bucket_duration: length of each bucket in seconds
    :return: A list of dicts with summary data.

    Sample dict:
    {
        'start_epoch': 1586552070,
        'time': datetime.datetime object,
        'count': 60,
        'successes': 59,
        'timeouts': 1,
        'success_rate': 0.0166667,
        'average': 23,
        'maximum': 45,
        'minimum': 12,
    }
    """
    buckets = []
    start_epoch = round_to_int(records[0]['time'].timestamp(), bucket_duration)
    count = 0
    successes = 0
    minimum = float('inf')
    maximum = 0
    total = 0
    for record in records:
        if record['time'].timestamp() >= start_epoch + bucket_duration:
            # record is in next bucket. tally totals for this bucket and add to output list
            if count > 0:
                bucket = {
                    'start_epoch': start_epoch,
                    'time': datetime.datetime.fromtimestamp(start_epoch),
                    'count': count,
                    'successes': successes,
                    'timeouts': count - successes,
                    'success_rate': successes / count,
                    'average': total / successes * 1000,
                    'maximum': maximum * 1000,
                    'minimum': minimum * 1000
                }
                buckets.append(bucket)
            # end of current bucket. zero the counters to start a new bucket.
            start_epoch = round_to_int(record['time'].timestamp(), bucket_duration)
            count = 0
            successes = 0
            minimum = float('inf')
            maximum = 0
            total = 0
        # count this record
        count += 1
        if record['latency'] != TIMEOUT_VALUE:
            successes += 1
            total += record['latency']
            if record['latency'] < minimum:
                minimum = record['latency']
            if record['latency'] > maximum:
                maximum = record['latency']
    return buckets


def make_graph_figure(pair, records, points=True, timeouts=True,
                      reduce=None, success_rate=False, minimum=False,
                      average=False, maximum=False):
    """ Make a graph for the given pair and list of records

    pair - dict - record from DB containing attributes of the src/dst pair.
    records - list of records from the time-series DB.
    points - T/F - draw the successful pings on the graph as points.
    timeouts - T/F - draw the timeouts on the graph as vertical lines.
    reduce - size of buckets/periods in seconds for decimating data. Or None to not reduce.
    success_rate - T/F - draw a line for ping success rate (right Y-axis) in each bucket.
    minimum - T/F - draw a line for the minimum response time in each bucket.
    maximum - T/F - draw a line for the maximum response time in each bucket.
    average - T/F - draw a line for the average response time in each bucket.

    The various T/F kwargs after the reduce kwarg are ignored if reduce is false-y.

    Returns a matplotlib figure
    """
    title = str.format("Ping Results {} to {}", pair.prober.name, pair.dst)
    success_times = []
    success_values = []
    timeout_times = []
    for record in records:
        if record['latency'] == TIMEOUT_VALUE:
            timeout_times.append(record['time'])
        else:
            success_times.append(record['time'])
            # multiply by 1000 for millis
            success_values.append(record['latency'] * 1000)
    figure, axes = ping_figure(success_times, success_values, timeout_times,
                               label=title, x_label="Time", y_label="Milliseconds")
    if reduce:
        buckets = reduce_data_points(records, reduce)
        bucket_times = [_['time'] for _ in buckets]
        axis2 = axes.twinx()
        if success_rate:
            success_rates = [_['success_rate'] for _ in buckets]
            axis2.set_ylabel("Success Rate")
            axis2.plot(bucket_times, success_rates, linestyle='-',
                       color='tab:green', marker='.', markersize=1)
    plt.tight_layout()  # re-calc position of axes, titles etc
    return figure


def _cleanup():
    # figure.clf()
    plt.close()


def make_graph_base64_png(pair, records):
    figure = make_graph_figure(pair, records)
    bytes_io = io.BytesIO()
    figure.savefig(bytes_io, format="png")
    b64_figure = base64.b64encode(bytes_io.getbuffer()).decode('utf-8')
    output = str.format("data:image/png;charset=utf-8;base64, {}", b64_figure)
    # clear the figure and close pyplot to prevent memory leaks
    _cleanup()
    return output


def make_graph_png(pair, records, **kwargs):
    figure = make_graph_figure(pair, records, **kwargs)
    bytes_io = io.BytesIO()
    figure.savefig(bytes_io, format="png")
    _cleanup()
    return bytes_io
