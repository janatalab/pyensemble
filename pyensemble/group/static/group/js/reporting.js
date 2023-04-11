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
        d3.select("#results_table thead").selectAll("tr")
            .data(Object.keys(data[0]))
            .enter()
            .append("th")
                .html(function(d){return d;})
                .attr("class", function(d){
                    if (d=='id'){
                        return "freeze-pane index";
                    }
                })

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
            .selectAll("td")
                .data(function(d){
                    return d3.entries(d);
                })
                .enter()
                .append("td")
                    .html(function(d){
                        return d.value
                    })
                    .attr("class", function(d){
                        if (d.key == 'id'){
                            return "freeze-pane index";
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