"""
Functions for generating graphs of the ping data
"""

import matplotlib.dates
matplotlib.use('agg')  # this does nothing if matplotlib.pyplot is imported
import matplotlib.pyplot as plt
import base64
import time
import io


locator = matplotlib.dates.AutoDateLocator()
formatter = matplotlib.dates.ConciseDateFormatter(locator)


def ping_figure(success_times, success_values, timeout_times,
                label="Ping Results", x_label=None, y_label=None):
    """ Plot ping results. No decimation.

    success_times - list of times (x-values on the graph).
    success_values - list of ping latencies (y-values on the graph).
    timeout_times - A list of times that had a timeout instead of a success.
    label - Optional title for the graph.
    x_label - Optional X-axis label for the graph
    y_label - Option Y-axis label for the graph.
    """
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
    plt.tight_layout()  # re-calc position of axes, titles etc
    return figure


def make_graph_figure(pair, records):
    """ Make a graph for the given pair and list of records"""
    title = str.format("Ping Results {} to {}", pair['src'], pair['dst'])
    success_times = []
    success_values = []
    timeout_times = []
    for record in records:
        if record[1] is None:
            timeout_times.append(record[0])
        else:
            success_times.append(record[0])
            # multiply by 1000 for millis
            success_values.append(record[1] * 1000)
    figure = ping_figure(success_times, success_values, timeout_times,
                         label=title, x_label="Time", y_label="Milliseconds")
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


def make_graph_png(pair, records):
    figure = make_graph_figure(pair, records)
    bytes_io = io.BytesIO()
    figure.savefig(bytes_io, format="png")
    _cleanup()
    return bytes_io
