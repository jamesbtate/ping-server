"""
Functions for generating graphs of the ping data
"""

import matplotlib
import matplotlib.dates
matplotlib.use('agg')  # this does nothing if matplotlib.pyplot is imported
import matplotlib.pyplot as plt
# from matplotlib import rcParams
# rcParams.update({'figure.autolayout': True})
# import numpy as np
import base64
import io

locator = matplotlib.dates.AutoDateLocator()
formatter = matplotlib.dates.AutoDateFormatter(locator)

def ping_figure(success_times, success_values, timeout_times,
                label=None, x_label=None, y_label=None):
    """ Plot ping results. No decimation.

    success_times - list of times (x-values on the graph).
    success_values - list of ping latencies (y-values on the graph).
    timeout_times - A list of times that had a timeout instead of a success.
    label - Optional title for the graph.
    x_label - Optional X-axis label for the graph
    y_label - Option Y-axis label for the graph.
    """
    figure, axes = plt.subplots()
    figure.suptitle("Ping Results")
    axes.xaxis.set_major_locator(locator)
    axes.xaxis.set_major_formatter(formatter)
    if label:
        figure.suptitle(label)
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
    #for t in timeout_times:
    #    axes.axvline(t, 0, 1, color='tab:red', linewidth=1)
    # figure.autofmt_xdate()  # rotate X-axis tick labels
    axes.tick_params(axis='x', labelrotation=30)
    return figure


def figure_to_base64(figure):
    """ Save a figure as a base64-encoded PNG suitable for an HTML <img> """
    bytes_io = io.BytesIO()
    figure.savefig(bytes_io, format="png")
    b64_figure = base64.b64encode(bytes_io.getbuffer()).decode('utf-8')
    output = str.format("data:image/png;charset=utf-8;base64, {}", b64_figure)
    return output