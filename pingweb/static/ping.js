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

function getSelectedCheckboxes(name) {
    /* return list of values of selected checkboxes with given name */
    let selected = [];
    $.each($("input[name='" + name + "']:checked"), function() {
        selected.push($(this).val());
    });
    return selected;
}

function multigraphClicked() {
    let selected = getSelectedCheckboxes("src_dst");
    if (selected.length == 0) {
        $("p#selected_action_error").html("No graphs selected");
        return;
    }
    let csv = selected.join(",");
    window.location.href = "/multigraph/" + csv;
}

$(document).ready(function() {
    $('.timepicker').datetimepicker({
        dateFormat: "yy-mm-dd",
        timeFormat: "HH:mm:ss",
    });
    /*startPicker = $('.timepicker#id_start_time').datetimepicker({
        dateFormat: "yy-mm-dd",
        timeFormat: "HH:mm:ss",
    });
    stopPicker = $('.timepicker#id_stop_time').datetimepicker({
        dateFormat: "yy-mm-dd",
        timeFormat: "HH:mm:ss",
        // altFormat: "@",
        // altField: "input#stop_alt",
        // altFieldTimeOnly: false,
        // altTimeFormat: "",
	    // altSeparator: ""
    });
    if (startPicker.length) {
        // startPicker.datetimepicker('setDate', (new Date($('.timepicker#id_start_time').data().initial * 1000)));
        // stopPicker.datetimepicker('setDate', (new Date($('.timepicker#id_stop_time').data().initial * 1000)));
    }*/

    $('input#go').click(goClicked);
    $('input#multigraph_button').click(multigraphClicked);
});