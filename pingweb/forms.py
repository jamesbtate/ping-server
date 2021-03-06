"""
Django forms not associated with a particular model.
"""
from typing import Tuple
from django import forms
from datetime import datetime
import misc


class GraphOptionsForm(forms.Form):
    window = forms.CharField(required=False, widget=forms.HiddenInput())
    start_time = forms.DateTimeField(required=False, widget=forms.TextInput(attrs={'class':'timepicker'}))
    stop_time = forms.DateTimeField(required=False, widget=forms.TextInput(attrs={'class':'timepicker'}))
    reduce = forms.BooleanField(required=False)
    points = forms.BooleanField(initial=True, required=False)
    timeouts = forms.BooleanField(initial=True, required=False)
    success_rate = forms.BooleanField(required=False)
    trim_x_axis = forms.BooleanField(required=False)

    def get_time_extents(self) -> Tuple[datetime, datetime]:
        """ Returns datetime.datetime start and stop times.

        Calculated from the start_time and stop_time values of this form.

        :return: (int, int)
        """
        window = self.cleaned_data['window']
        start = None
        stop = None
        if 'start_time' in self.cleaned_data:
            start = self.cleaned_data['start_time']
        if 'stop_time' in self.cleaned_data:
            stop = self.cleaned_data['stop_time']
        return misc.get_time_extents_from_params(window, start, stop)

    def set_datetime_fields(self, start, stop) -> None:
        """ Set the datetime values for the start_time and stop_time fields. """
        self.data = self.data.copy()
        self.data['start_time'] = start
        self.data['stop_time'] = stop
        self.initial['start_time'] = start
        self.initial['stop_time'] = stop

    def set_field_defaults(self):
        for field in self.fields:
            if field not in self.data:
                self.data[field] = self.fields[field].initial

    @classmethod
    def prepare_form_from_get(cls, request_get):
        """ Initialize the form with values from request.GET """
        graph_options_form = GraphOptionsForm(request_get)
        if graph_options_form.is_valid():
            start_time, stop_time = graph_options_form.get_time_extents()
        else:
            start_time, stop_time = misc.get_time_extents_from_params('1h')
        graph_options_form.set_datetime_fields(start_time, stop_time)
        graph_options_form.set_field_defaults()
        return graph_options_form
