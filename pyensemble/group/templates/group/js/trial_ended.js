// group_trial_ended.js

function group_trial_ended(){
    // Check the current trial state
    $.ajax({
        dataType: "json",
        url: "{% url 'pyensemble-group:group_trial_status' %}",
        type: 'GET',
        data: {},
        success: function(data){
            if (data.state == 'trial:ended'){
                $('#questions').removeClass('d-none');
            } else {
                setTimeout(group_trial_ended, 500);
            }
        },
        error: function(response,errorText){
          alert(response.responseText);
        }
    });
}

// Set the initial timeout
setTimeout(group_trial_ended, 500);