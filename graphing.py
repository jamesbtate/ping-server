"""
Functions for generating graphs of the ping data
"""

import matplotlib.pyplot as plt
import numpy as np


def ping_figure(time_array, value_array, label=None):
    """ Plot ping results. No decimation. """
    figure, axes = plt.subplots()
    figure.suptitle("Ping Results")
    axes.plot(time_array, value_array, label=label)
    return figure


def figure_to_base64(figure):
    """ Save a figure as a base64-encoded PNG suitable for an HTML <img> """
    todo = 1
