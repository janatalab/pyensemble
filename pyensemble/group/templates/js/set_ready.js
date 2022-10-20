// set_ready.js

// Indicate that the client is ready
$.ajax({
    dataType: "json",
    url: "{% url 'pyensemble-group:set_client_ready' %}",
    type: 'POST',
    data: {},
    success: function(data){
    },
    error: function(response,errorText){
      alert(response.responseText);
    }
});
