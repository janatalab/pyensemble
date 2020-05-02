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
        var itemType = ev.target.innerText;
        var url = '/'+itemType.toLowerCase()+'/';

        // Get listing of the items
        $.ajax({
            url: url,
            type: 'GET',
            success: function(response){
                $("#content-right").addClass('d-none');

                $("#contentListHeader").text(itemType);
                $("#addButton").text('Add '+itemType.slice(0,itemType.length-1));
                $("#addButton").on('click',function(ev){
                    ev.preventDefault();

                    var url = '/'+itemType.toLowerCase()+'/create/';
                    fetchDetailContent(url);
                })

                $("#contentListContent").html(response);
                bindListItems();
            },
            error: function(jqXHR, textStatus, errorThrown){
                alert(jqXHR.responseText);
            },
            complete: function(){
                // Clear detail content
                $("#content-left").removeClass('d-none');
            }
        });
    });
}

function fetchDetailContent(url){
    $.ajax({
        url: url,
        type: 'GET',
        success: function(response){
            $("#content-right").html(response);
            $("#content-right").addClass('col-12');
            $("#content-right").removeClass('d-none');
        },
        error: function(jqXHR, textStatus, errorThrown){
            alert(jqXHR.responseText);
        },
        complete: function(){
            $("#content-left").addClass('d-none');
        }
    });
}

function bindListItems(){
    var $table = $("#contentListContent table");
    $table.attr('data-show-header','false');
    $table.bootstrapTable();
    $table.bootstrapTable('hideColumn','checkbox');

    $(".contentlist-item-link").on('click',function(ev){
        ev.preventDefault();

        fetchDetailContent(ev.target.href);
        // $.ajax({
        //     url: ev.target.href,
        //     type: 'GET',
        //     success: function(response){
        //         $("#content-right").html(response);
        //         $("#content-right").addClass('col-12');
        //         $("#content-right").removeClass('d-none');
        //     },
        //     error: function(jqXHR, textStatus, errorThrown){
        //         alert(jqXHR.responseText);
        //     },
        //     complete: function(){
        //         $("#content-left").addClass('d-none');
        //     }
        // });
    });
}

function submitEditorForm(){
    var form=$("#editorForm");
    $.ajax({
        type: form.attr('method'),
        url: form.attr('action'),
        data: form.serialize(),
        success: function(response){
            $("#content-right").html(response);
        },
        error: function(response){
            alert(response.responseText);
        }
    });
}

function fetchFormList(){
    $.ajax({
        url: '/forms/',
        type: 'GET',
        data: {'type':'form_select'},
        success: function(response){
          $("#addFormTable .modal-body").html(response);
          $("#addFormTable table").bootstrapTable();
        },
        error: function(response,errorText){
          alert(response.responseText);
        }
    });
}

function submitFormAdditions(){
    data = $("#addFormTable table").bootstrapTable('getAllSelections').map(function(d){return d.name});
    experiment_id = $("#experiment_id").val();
    $.ajax({
        url: '/forms/add/'+experiment_id+'/',
        type: 'POST',
        data: JSON.stringify(data),
        success: function(response){
            $("#content-right").html(response);
        },
        error: function(response){
            alert(response.responseText);
        }
    })
}


$(document).ready(function () {
    // Bind navigation functions functions
    bindFunctions();
});