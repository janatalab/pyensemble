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

$(document).ready(function () {
    // Bind navigation functions functions
    bindFunctions();
});

function bindFunctions(){
    $(".content-link").on('click', function(ev){
        ev.preventDefault();

        var itemType = ev.target.innerText;

        $.ajax({
            url: ev.target.href,
            type: 'GET',
            dataType: 'html',
            success: function(response){
                $("#content-right").addClass('d-none');

                $("#contentListHeader").text(itemType);
                $("#addButton").text('Add '+itemType.slice(0,itemType.length-1));
                $("#addButton").on('click',function(ev){
                    ev.preventDefault();

                    var itemType = this.innerText;
                    var url = itemType.slice(itemType.search(' ')+1,).toLowerCase()+'s/create/';
                    fetchDetailContent(url);
                })

                $("#contentListContent").html(response);

                var $table = $("#contentListContent table");
                $table.attr('data-show-header','false');

                // Sometimes, bootstrapTable doesn't bind to the element
                if (!$table.bootstrapTable){
                    alert('bootstrapTable did not bind to loaded table!\nReload the browser window.')
                }

                $table.bootstrapTable();
                $table.bootstrapTable('hideColumn','checkbox');
                $table.on('page-change.bs.table',function(){
                    bindContentListItems();
                })

                bindContentListItems();
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

function bindContentListItems(){
    $(".contentlist-item-link").on('click',function(ev){
        ev.preventDefault();
        fetchDetailContent(ev.target.href);
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

function fetchItemList(item_type){
    $.ajax({
        url: item_type+'/',
        type: 'GET',
        data: {'type':'select'},
        success: function(response){
          $("#addItemTable .modal-body").html(response);
          $("#addItemTable table").bootstrapTable();
        },
        error: function(response,errorText){
          alert(response.responseText);
        }
    });
}

function submitItemAdditions(item_type){
    data = $("#addItemTable table").bootstrapTable('getAllSelections').map(function(d){return d.name});
    parent_id = $("#parent_id").val();
    $.ajax({
        url: item_type+'/add/'+parent_id+'/',
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

function submitEditorForm(){
    var form=$(".editor-form");
    $.ajax({
        type: form.attr('method'),
        url: form.attr('action'),
        data: form.serialize(),
        success: function(response){
            $("#content-right").html(response);
        },
        error: function(response){
            $("#content-right").html();
            alert(response.responseText);
        }
    });
}

function submitForm(target){
    $.ajax({
        type: target.attr('method'),
        url: target.attr('action'),
        data: target.serialize(),
        success: function(response){
            $("#content-right").html(response);
        },
        error: function(response){
            $("#content-right").html();
            alert(response.responseText);
        }
    });
}

function setEditStatus(status){
    if (status === undefined){
        status = true;
    }

    if (!status){
        $("#content-right input,textarea").attr({'readonly':false});
        $("#content-right input:checkbox").attr({'disabled':false});
        $("#content-right .dateinput").attr({'disabled':false});
        $(".editor.form-actions").removeClass('d-none');
        $("#formTableEditButton").addClass('btn btn-danger active');
    } else {
        $("#content-right input,textarea").attr({'readonly':true});
        $("#content-right input:checkbox").attr({'disabled':true});
        $("#content-right .dateinput").attr({'disabled':true});
        $(".editor.form-actions").addClass('d-none');
        $("#formTableEditButton").removeClass('btn-danger active');
    }
}

function toggleEditStatus(){
    var new_status = $("#content-right input,textarea").attr('readonly') == 'readonly' ? false : true;

    setEditStatus(new_status);
}