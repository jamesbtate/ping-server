var startPicker, stopPicker;

function goClicked() {
    console.log("Go clicked");
    var start = startPicker.datetimepicker("getDate").getTime() / 1000;
    var stop = stopPicker.datetimepicker("getDate").getTime() / 1000;
    var newURL = new URL(window.location.href);
    console.log(start, stop);
    newURL.searchParams.set('start_time', start);
    newURL.searchParams.set('stop_time', stop);
    newURL.searchParams.delete('window');
    console.log(newURL.href);
    window.location.href = newURL.href;
}

$(document).ready(function() {
    startPicker = $('.timepicker#id_start_time').datetimepicker({
        dateFormat: "yy-mm-dd",
        timeFormat: "HH:mm:ss",
    });
    stopPicker = $('.timepicker#id_stop_time').datetimepicker({
        dateFormat: "yy-mm-dd",
        timeFormat: "HH:mm:ss",
        /*altFormat: "@",
        altField: "input#stop_alt",
        altFieldTimeOnly: false,
        altTimeFormat: "",
	    altSeparator: ""*/
    });
    if (startPicker.length) {
        // startPicker.datetimepicker('setDate', (new Date($('.timepicker#id_start_time').data().initial * 1000)));
        // stopPicker.datetimepicker('setDate', (new Date($('.timepicker#id_stop_time').data().initial * 1000)));
    }

    $('input#go').click(goClicked);
});