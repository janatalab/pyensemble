// editor.js
var csrftoken = $.cookie('csrftoken');

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFTOKEN", csrftoken);
        }
    }
});

function bindFunctions(){
    $(".content-link").on('click', function(ev){
        var itemType = ev.target.innerText.toLowerCase();
        // var url = ev.target.host+'/'+itemType+'/';
        var url = '/'+itemType+'/';

        // Get listing of the items
        $.ajax({
            url: url,
            type: 'GET',
            success: function(response){
                $("#contentListContent").html(response);
                bindListItems();
            },
            error: function(jqXHR, textStatus, errorThrown){
                alert(jqXHR.responseText);
            },
            complete: function(){
                // Clear detail content
                $("#detailContent").addClass('d-none');
            }
        });
    });
}

function bindListItems(){
    $(".contentlist-item-link").on('click',function(ev){
        ev.preventDefault();

        $.ajax({
            url: ev.target.href,
            type: 'GET',
            success: function(response){
                $("#detailContent").html(response);
                $("#detailContent").removeClass('d-none');
            },
            error: function(jqXHR, textStatus, errorThrown){
                alert(jqXHR.responseText);
            },
            complete: function(){

            }
        });
    });
}

$(document).ready(function () {
    // Bind navigation functions functions
    bindFunctions();
});