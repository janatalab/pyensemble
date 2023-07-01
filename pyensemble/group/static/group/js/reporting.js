// reporting.js

// $(function() {
window.PyEnsemble.reporting = (function(){
    var core = {};

    core.urls = JSON.parse(document.getElementById('group-urls').textContent);

    function onChangedSelection(e, clickedIndex, isSelected, previousValue) {

        var level = e.target.name.toLowerCase();
        var item_id = e.target.options[clickedIndex].value;
        var url = "";

        if (level == 'experiment'){
            // Update menu items for session dropdown
            $.ajax({
                url: core.urls['experiment-session-selector'],
                type: 'GET',
                data: {'id': item_id,},
                dataType: 'html',
                success: function(response){
                    $("#session-list").html(response);
                    $(".selectpicker[name='session']")
                        .selectpicker('show')
                        .on('changed.bs.select', onChangedSelection);
                },
                complete: function(){
                    $("#results_table").html("");
                }
            });

            // Get ourselves an experiment analysis nav               
            $.ajax({
                url: core.urls['experiment-analysis-nav'],
                type: 'GET',
                data: {'id': item_id,},
                dataType: 'html',
                success: function(response){
                    $("#secondary-navbar").html(response);
                    $(".analysis-item").on('click', onAnalysisRequest)
                },
            });

        }
        else if (level == "session"){
            $.ajax({
                url: core.urls['session-detail'],
                type: 'GET',
                data: {'id': item_id},
                dataType: 'html',
                success: function(response){
                    $("#results_table").html(response);
                },
            });
        }
    }

    $('.selectpicker').selectpicker()
        .on('changed.bs.select', onChangedSelection);


    core.populateTable = function(data){
        // Create our basic table
        if (d3.select("#results_table").select("table").empty()){
            var table = d3.select("#results_table").append("table").attr("class","reporting table table-striped table-bordered table-sm"),
                thead = table.append("thead").attr("class","reporting"),
                tbody = table.append("tbody").attr("class","reporting");            
        } else {
            var thead = d3.select("#results_table thead");
            var tbody = d3.select("#results_table tbody");
        }

        // Add column labels
        var header_row = thead.select("tr");

        if (header_row.empty()){
            header_row = thead.append("tr");
        } 
        
        column_labels = header_row.selectAll("th")
            .data(Object.keys(data[0]).filter(d => d!="meta"));

        column_labels.enter()
            .append("th")
                .html(function(d){return d;})
                .attr("class", function(d){
                    if (d=='id'){
                        return "freeze-pane index";
                    }

                    if (d=='notes'){
                        return "reporting-notes-col";
                    }
                });

        column_labels.exit().remove()

        // Add rows
        let sessions = d3.select("#results_table tbody").selectAll("tr")
            .data(data, function(d){
                return d.id;
            });

        // Remove rows for removed sessions
        sessions.exit().remove();    

        // Create rows for any new sessions        
        sessions.enter()
            .append("tr")
                .attr("class", function(d){
                    let base_class = "groupsession-data";
                    
                    if (d.meta.all_completed) base_class += " groupsession-all-complete"
                    
                    return base_class
                })
                .attr("id", function(d){
                    return "groupsession-"+d.id;
                })
            .selectAll("td")
                .data(function(d){
                    return d3.entries(d).filter(function(d) {return d.key != "meta"})
                })
                .enter()
                .append("td")
                    .html(function(d){
                        if (d.key == 'subjects'){
                            return "<table class='subject-info'>"

                        } else if (d.key == 'id'){
                            let val = d.value;

                            val += "<div class='text-danger'>Exclude <input type='checkbox' class='session exclude-checkbox' id='"+d.value+"-exclude' ></div>";

                            val += "<button type='button' class='btn btn-outline-info attach-file-btn' id='attach-file-"+d.value+"' data-toggle='modal' data-target='#attachFileModal' data-session='"+d.value+"'>Attach File</button>";

                            return val
                        } else {
                           return d.value
                        }
                    })
                    .attr("class", function(d){
                        var class_str = "align-middle";

                        if (d.key == 'id'){
                            class_str += " freeze-pane index";
                        }

                        return class_str
                    });

        sessions.select("table.subject-info").selectAll('tr')
            .data(function(d){
                return d.subjects
            }, function(s){
                return s.subject_id
            })
            .enter()
            .append("tr")
                .selectAll("td")
                .data(function(d){
                    return d3.entries(d)
                })
                .enter()
                .append("td")
                    .html(function(s){
                        if (s.key == "last_response"){
                            if (s.value){
                                return Object.values(s.value).join(', ')
                            } else {
                                return "No responses"
                            }
                        } else {    
                            return s.value
                        }
                    })

        d3.selectAll(".session.exclude-checkbox").on("change", excludeGroupSession);
        $('.attach-file-btn').on('click', function(){
            // Set the session ID on the modal
            document.querySelector(this.dataset.target).dataset.session = this.dataset.session;
        });

    }

    function excludeGroupSession(){
        if (!this.checked) {return};

        $(".exclude-checkbox").attr("disabled", true);

        let session_id = this.id.match(/(\w*)-exclude/)[1];

        $.ajax({
                url: core.urls['exclude-groupsession'],
                type: 'POST',
                dataType: "json",        
                data: {
                    'session': session_id
                },
                success: function(data){
                    let row_id = "#groupsession-"+session_id;
                    d3.select(row_id).remove();
                },
                error: function(response,errorText){
                    alert(response.responseText);
                },
                complete: function(){
                    $(".exclude-checkbox").attr("disabled", false);
                }
        });
    }

    function onAnalysisRequest(ev){
        ev.stopImmediatePropagation();
        ev.preventDefault();

        $.ajax({
            url: ev.target.href,
            type: 'GET',
            data: {'experiment_id': $(".selectpicker[name='Experiment']").val()},
            dataType: 'json',
            success: function(data){
                core.populateTable(data['sessions']);
            },
        });
    };

    core.fetchAttachFileForm = function(ev){
        var session_id = ev.dataset.session;
        // Fetch our groupsession file upload form
        var url = core.urls['attach-file'];
        $.ajax({
            url: url,
            type: 'GET',
            dataType: "html",        
            data: {
                'session_id': session_id,
            },
            success: function(response){
                $(ev).find(".modal-body").html(response);
                $(ev).find("form").attr({action:url});
            },
            error: function(response){
                alert('Unable to fetch file attachment form ...')
            }
        });        
    }

    return core
})();