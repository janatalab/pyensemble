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
                $("#contentListHeader").removeClass('d-none');
                $("#contentListContent").html(response);
                bindListItems();
            },
            error: function(jqXHR, textStatus, errorThrown){
                alert(jqXHR.responseText);
            },
            complete: function(){
                // Clear detail content
                // $("#detailContent").addClass('d-none');
                $("#content-left").removeClass('d-none');
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
                $("#content-right").html(response);
                $("#content-right").addClass('col-12');
                $("#content-right").removeClass('d-none');

                // Only want to attach a table if we are in the experiment or form editor
                // Regexp the url to get the item type
                // $('#ftable').bootstrapTable();
                // $('#ftable').on('reorder-row.bs.table', updateFormOrder);
            },
            error: function(jqXHR, textStatus, errorThrown){
                alert(jqXHR.responseText);
            },
            complete: function(){
                $("#content-left").addClass('d-none');
            }
        });
    });
}

function updateFormOrder(ev,rows){
    alert(rows);
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
        url: '/forms/add/',
        type: 'GET',
        success: function(response){
          $("#formTable tbody").html(response);
          $('#addFormTable').bootstrapTable('resetView');
        },
        error: function(response,errorText){
          alert(response.responseText);
        }
    });
}

function submitFormAdditions(){
    data = $("#formTable").bootstrapTable('getAllSelections').map(function(d){return d.name});
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