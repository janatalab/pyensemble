function get_participant_state(){
    $.ajax({
        dataType: "json",
        url: "{% url 'pyensemble-group:groupuser_state' %}",
        type: 'GET',
        data: {},
        success: function(data){
            if (data == 'RESPONSE_PENDING'){
                $('#questions').removeClass('d-none');
            } else if (data == 'EXIT_LOOP'){
                exit_loop();
            } else {
                setTimeout(get_participant_state, 500);
            }
        },
        error: function(response, errorText){
          alert(response.responseText);
        }
    });
}

// Set the initial timeout
setTimeout(get_participant_state, 500);

function exit_loop(){
    $.ajax({
        type: 'GET',
        url: "{% url 'pyensemble-group:groupuser_exitloop' %}",
        success: function(response){
            document.open();
            document.write(response);
            document.close();
        },
    });
}