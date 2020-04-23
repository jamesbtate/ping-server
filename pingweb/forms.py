"""
Django forms not associated with a particular model.
"""
from typing import Tuple
from django import forms
from datetime import datetime as dt
import misc


class GraphOptionsForm(forms.Form):
    window = forms.CharField(required=False, widget=forms.HiddenInput())
    start_time = forms.DateTimeField(required=False, widget=forms.TextInput(attrs={'class':'timepicker'}))
    stop_time = forms.DateTimeField(required=False, widget=forms.TextInput(attrs={'class':'timepicker'}))
    reduce = forms.BooleanField(required=False)
    points = forms.BooleanField(initial=True, required=False)
    timeouts = forms.BooleanField(initial=True, required=False)
    success_rate = forms.BooleanField(required=False)

    def get_time_extents(self) -> Tuple[int, int]:
        """ Returns integer start and stop times calculated from the datetime.datetime values.

        :return: (int, int)
        """
        window = self.cleaned_data['window']
        start = self.cleaned_data['start_time']
        if start:
            start = int(start.timestamp())
        stop = self.cleaned_data['stop_time']
        if stop:
            stop = int(stop.timestamp())
        return misc.get_time_extents_from_params(window, start, stop)

    def set_datetime_fields(self, start, stop) -> None:
        """ Set the datetime values for the start_time and stop_time fields. """
        start_timestamp = dt.fromtimestamp(start)
        stop_timestamp = dt.fromtimestamp(stop)
        # self.cleaned_data['start_time'] = start_timestamp
        # self.cleaned_data['stop_time'] = stop_timestamp
        self.data = self.data.copy()
        self.data['start_time'] = start_timestamp
        self.data['stop_time'] = stop_timestamp
        self.initial['start_time'] = start_timestamp
        self.initial['stop_time'] = stop_timestamp

    def set_field_defaults(self):
        for field in self.fields:
            if field not in self.data:
                self.data[field] = self.fields[field].initial
