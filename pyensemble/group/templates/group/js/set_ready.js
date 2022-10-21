// set_ready.js

// Indicate that the client is ready
// Have to delay in order to preserve state long enough for all other participants to catch up
setTimeout(function (){
    $.ajax({
        dataType: "json",
        headers: {"X-CSRFToken": $.cookie('csrftoken')},
        url: "{% url 'pyensemble-group:set_client_ready' %}",
        type: 'POST',
        data: {},
        success: function(data){
        },
        error: function(response,errorText){
          alert(response.responseText);
        }
    });
  }, 500);

