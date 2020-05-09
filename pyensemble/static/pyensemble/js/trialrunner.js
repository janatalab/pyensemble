// trialrunner.js
//
// Sets things up to run a trial in jsPsych
// Assumes jsPsych setup from scratch

function post_trial(trialdata){
    // Write any responses that were obtained to a hidden field in our Django form
    // Add this as a text form field that we can write a JSON-encoded dict to
    // This can be included as an extra jsPsych form to be passed along to the template.
    $('input[name="jspsych_data"]').val(JSON.stringify(trialdata));

    // Hide the trialrunner div
    $("#trialrunner").addClass("d-none");

    // Unmask the div containing the questions
    $("#questions").removeClass("d-none");

}

function start_trial(timeline){
    var options = {};
    options.display_element = document.querySelector('#trialrunner');
    options.timeline = timeline;
    options.show_progress_bar = false;
    options.on_finish = post_trial;

    // Initialize jsPsych
    jsPsych.init(options);

}
