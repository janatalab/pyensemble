// reporting.js

$(function() {
    const urls = JSON.parse(document.getElementById('group-urls').textContent);

    function onChangedSelection (e, clickedIndex, isSelected, previousValue) {

        var level = e.target.name.toLowerCase();
        var item_id = e.target.options[clickedIndex].value;
        var url = "";

        if (level == 'experiment'){
            // Update menu items for session dropdown
            $.ajax({
                url: urls['experiment-session-selector'],
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
                url: urls['experiment-analysis-nav'],
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
                url: urls['session-detail'],
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

    function populateTable(data){
        // Create our basic table
        if (d3.select("#results_table").select("table").empty()){
            var table = d3.select("#results_table").append("table").attr("class","reporting table table-striped table-bordered table-sm"),
                thead = table.append("thead").attr("class","reporting"),
                tbody = table.append("tbody").attr("class","reporting");            
        };

        // Add column labels
        if (thead.select("tr").empty()){
            var header_row = thead.append("tr");
        }
        
        column_labels = header_row.selectAll("th")
            .data(Object.keys(data[0]));

        column_labels.enter()
            .append("th")
                .html(function(d){return d;})
                .attr("class", function(d){
                    if (d=='id'){
                        return "freeze-pane index";
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
                .classed("groupsession-data", true)
                .attr("id", function(d){
                    return "groupsession-"+d.id;
                })
            .selectAll("td")
                .data(function(d){
                    return d3.entries(d);
                })
                .enter()
                .append("td")
                    .html(function(d){
                        if (d.key == 'subjects'){
                            return "<table class='subject-info'>"

                        } else if (d.key == 'id'){
                            let val = d.value;

                            val += "<div class='text-danger'>Exclude <input type='checkbox' class='session exclude-checkbox' id='"+d.value+"-exclude' ></div>";
                            return val
                        } else {
                           return d.value
                        }
                    })
                    .attr("class", function(d){
                        if (d.key == 'id'){
                            return "freeze-pane index";
                        }
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
    }

    function excludeGroupSession(){
        if (!this.checked) {return};

        $(".exclude-checkbox").attr("disabled", true);

        let session_id = this.id.match(/(\w*)-exclude/)[1];

        $.ajax({
                url: urls['exclude-groupsession'],
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
                populateTable(data['sessions']);
                // $("#results_table").html(response);
            },
        });
    };

});