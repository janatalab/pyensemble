function post_trial(data){
    // Write any responses that were obtained to a hidden field in our Django form
    $('input[name="jspsych_data"]').val(JSON.stringify(data.values()));

    // Hide the trialrunner div
    $("#trialrunner").addClass("d-none");

    // Unmask the div containing the questions
    $("#questions").removeClass("d-none");

    $("#questions .form-actions input").attr({'disabled':false})

}

function start_trial(timeline){
    var options = {};
    options.display_element = document.querySelector('#trialrunner');
    options.timeline = timeline;
    options.show_progress_bar = false;
    options.on_finish = post_trial;

    $("#questions .form-actions input").attr({'disabled':true})

    // Initialize jsPsych
    jsPsych.init(options);

}
