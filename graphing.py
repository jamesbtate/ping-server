"""
Functions for generating graphs of the ping data
"""

import matplotlib.pyplot as plt
import numpy as np
import base64
import io


def ping_figure(time_array, value_array, label=None):
    """ Plot ping results. No decimation. """
    figure, axes = plt.subplots()
    figure.suptitle("Ping Results")
    axes.plot(time_array, value_array, label=label)
    return figure


def figure_to_base64(figure):
    """ Save a figure as a base64-encoded PNG suitable for an HTML <img> """
    bytes_io = io.BytesIO()
    figure.savefig(bytes_io, format="png")
    b64_figure = base64.b64encode(bytes_io.getbuffer())
    output = str.format("data:image/jpeg;charset=utf-8;base64, %s", b64_figure)
    return output