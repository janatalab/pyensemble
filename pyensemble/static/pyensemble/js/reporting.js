// reporting.js

// $(function() {
window.PyEnsemble.reporting = (function(){
    var core = {};

    core.urls = JSON.parse(document.getElementById('reporting-urls').textContent);

    core.currentAnalysisLevel = undefined;

    core.resetCurrentSelections = function(){
        core.currentSelections = {
            study: undefined,
            experiment: undefined,
            subject: undefined,
            session: undefined,
        };
    };

    core.resetCurrentSelections();

    function onChangedSelection(e, clickedIndex, isSelected, previousValue) {

        var level = e.target.name.toLowerCase();
        var item_id = e.target.options[clickedIndex].value;

        // Cache our current selection value
        core.currentAnalysisLevel = level;

        core.resetCurrentSelections();
        core.currentSelections[level] = item_id;

        $('.selectpicker').each(function(){
            if (this.name != level){
                this.value = undefined;
                $(this).selectpicker("refresh");
            }
        });

        $("#secondary-navbar").addClass("d-none");

        $("#session_list_table").html("");

        var url = "";

        if (level == 'study'){
            $.ajax({
                url: core.urls['study-analysis-nav'],
                type: 'GET',
                data: {'id': item_id,},
                dataType: 'html',
                success: function(response){
                    $("#secondary-navbar").html(response);
                    $(".analysis-item").on('click', onAnalysisRequest);
                    $("#secondary-navbar").removeClass("d-none");
                },
            });
        } else if (level == 'experiment'){
            // Update menu items for session dropdown
            // $.ajax({
            //     url: core.urls['experiment-session-selector'],
            //     type: 'GET',
            //     data: {'id': item_id,},
            //     dataType: 'html',
            //     success: function(response){
            //         // $("#session-list").html(response);
            //         // $(".selectpicker[name='session']")
            //         //     .selectpicker('show')
            //         //     .on('changed.bs.select', onChangedSelection);
            //     },
            //     complete: function(){
            //         $("#session_list_table").html("");
            //     }
            // });

            // Get ourselves an experiment analysis nav               
            $.ajax({
                url: core.urls['experiment-analysis-nav'],
                type: 'GET',
                data: {'id': item_id,},
                dataType: 'html',
                success: function(response){
                    $("#secondary-navbar").html(response);
                    $(".analysis-item").on('click', onAnalysisRequest);
                    $("#secondary-navbar").removeClass("d-none");

                },
            });

        } else if (level == "session"){
            $.ajax({
                url: core.urls['session-detail'],
                type: 'GET',
                data: {'id': item_id},
                dataType: 'html',
                success: function(response){
                    $("#session_list_table").html(response);
                },
            });
        }
    }

    $('.selectpicker').selectpicker()
        .on('changed.bs.select', onChangedSelection);

    function onAnalysisRequest(ev){
        ev.stopImmediatePropagation();
        ev.preventDefault();

        // Get our selected experiment
        // var experiment_id = $(".selectpicker[name='Experiment']").val();
        var dataType = "json";

        if (ev.target.text == 'Responses'){
            dataType = "html";
        }

        $.ajax({
            url: ev.target.href,
            type: 'GET',
            data: core.currentSelections,
            dataType: dataType,
            success: function(data){
                // Determine what kind of data we're dealing with
                // core.populateTable(data['session_data']);

                if (dataType == "json"){
                    updateResults(data);

                } else {
                    document.open();
                    document.write(data);
                    document.close();
                }
            },
            error: function(response){
                alert(response.responseText)
            },
        });
    };

    function excludeSession(){
        $(".exclude-session-btn").attr("disabled", true);

        var identifier = this.id.match(/exclude-(.*)/)[1];

        var session_id = subject_id = undefined;
        var url = undefined;

        // Try first for session ID
        session_id = identifier.match(/^\d+$/)[0];

        if (!session_id) subject_id = identifier.match(/^\w+$/)[0];
        
        core.currentSelections.session = session_id;
        core.currentSelections.subject = subject_id;
        
        url = session_id ? core.urls['exclude-session'] : subject_id ? core.urls['exclude-subject'] : undefined;

        $.ajax({
                url: url,
                type: 'POST',
                dataType: "html",        
                data: core.currentSelections,
                success: function(data){
                    let row_id = "#entry-"+identifier;
                    d3.select(row_id).remove();
                },
                error: function(response,errorText){
                    alert(response.responseText);
                },
                complete: function(){
                    $(".exclude-session-btn").attr("disabled", false);
                }
        });
    }

    function parseColumnTuple(t){
        return t.split(",").map(function(d){return d.match(/\b.*\b/)[0]})
    }

    function extractSessionIDs(subject_info){
        let session_ids = Object.keys(subject_info)
            .filter(function(d){
                return (d.match(/session_id/) && subject_info[d]) ? true : false;
            })
            .map(function(d){return subject_info[d];});

        return session_ids
    }

    function updateStatsHighlighting(){
        // Get our total number of variables
        var numVariables = d3.selectAll(".variable-label").size();
        var stepSize = Math.floor(255/numVariables);

        // Parse the ID
        let parsed_id = this.id.split("-");

        let stat_type = parsed_id.pop();

        // Get the min and max values
        var min = Number(d3.select(this.parentNode).select("input.min").property("value"))
        var max = Number(d3.select(this.parentNode).select("input.max").property("value"));

        // Select items matching this class' experiment and variable IDs
        let select_str = "td."+parsed_id.reduce((o,s)=>o+"."+s)
        d3.selectAll(select_str)
            .classed("outlier", false)
            .style("background-color", "#ffffff")
            .filter(function(d){
                return (d.value < min) || (d.value > max)
            })
            .classed("outlier", true)
            .style("background-color", function(d){
                
                let colorVal = 255-stepSize;
                return "#ff"+colorVal.toString(16)+colorVal.toString(16)
            });

        // Update subject aggregate colors
        d3.selectAll(".participant-data").each(function(d){
            let target = d3.select(this);
            let numBad = target.selectAll(".outlier").size();
            let colorVal = 255-stepSize*numBad;

            target.select("td").style("background-color", "#ff"+colorVal.toString(16)+colorVal.toString(16));
        });
    }

    function updateResults(data){
        // Determine what type of data we are dealing with
        if (data.type == 'study_data'){
            // $("#item_title").text(data.title);

            for (stat in data.stats){
                data.stats[stat] = JSON.parse(data.stats[stat]);
            }

            data.experiment_data = JSON.parse(data.experiment_data);
        } else if (data.type == 'experiment_data'){

        }

        // Bind the data to the session table
        bindData(data);
    }
    
    function bindData(data){
        // Extract the column labels
        let column_tuples = undefined;
        var entry_data = undefined;

        if (data.type == "study_data"){
            entry_data = data.experiment_data;

        } else if (data.type == "experiment_data"){
            entry_data = data.session_data;
        }

        // Extract the column labels
        column_tuples = Object.keys(Object.values(entry_data)[0]);

        // Build the column header
        let level_items = column_tuples.map(parseColumnTuple);

        let num_levels = level_items[0].length;

        // Initialize our levels array
        let levels = [];

        for (let l=0; l<num_levels; l++){
            levels[l] = {}
            
            levels[l].key = num_levels > 1 ? l ? "variable" : "experiment" : "variable";
            levels[l].value = level_items.map(function(d){return d[l]});
        }

        // Verify the number of levels
        if (num_levels > 1) {
            let counter = {};

            for (item of levels[0].value){
                if (counter[item]) {
                    counter[item] += 1;
                } else {
                    counter[item] = 1;
                }
            };

            // Replace levels[0] with the counter data
            levels[0].value = [{"key": "index-label", "value": "ID"}].concat(d3.entries(counter));
        } else {
            levels[0].value = ["ID"].concat(levels[0].value);
        }

        // Create our basic table
        if (d3.select("#session_list_table").select("table").empty()){
            var table = d3.select("#session_list_table").append("table").attr("class","reporting table table-bordered table-sm"),
                thead = table.append("thead").attr("class","reporting"),
                tbody = table.append("tbody").attr("class","reporting");            
        };

        // Add the column labels
        d3.select("#session_list_table thead").selectAll("tr")
            .data(levels, function(d){return d.key;})
            .enter()
            .append("tr")
            .selectAll("th")
                .data(function(d){return d.value;})
                .enter()
                .append("th")
                    .attr("rowspan", function(d){
                        return d.key=="index-label" ? levels.length : 1;
                    })
                    .attr("colspan", function(d){
                        return d.key=="index-label" ? 1 : d.value;
                    })
                    .attr("class", function(d, i){
                        if (d.key == "index-label"){
                            return "freeze-pane index";
                        } else {
                            let type = d3.select(this.parentNode).datum().key;
                            if (type == "experiment"){
                                return d.key;
                            } else {
                                let retval = "";
                                if (num_levels > 1){
                                    retval = level_items[i][0] + " " + d;
                                } else {
                                    if (i == 0) retval = "freeze-pane index";
                                }
                                return retval
                            }
                        }
                    })
                    .html(function(d, i){
                        if (d.key=="index-label"){
                            return d.value;
                        } else {
                            let type = d3.select(this.parentNode).datum().key;
                            if (type == "experiment"){
                                return d.key;
                            } else {
                                let str = "";
                                str += "<div class='variable-label'>"+d+"</div>";

                                if (i > 0){
                                    let experiment_str = num_levels > 1 ? level_items[i][0]+"-" : "";

                                    let min_label = experiment_str+d+"-min";
                                    let max_label = experiment_str+d+"-max";

                                    str += "<div class='stats'>";

                                    str += "<label for='"+min_label+"'>";
                                    str += "Min";
                                    str += "</label>";
                                    str += "<input type='number' class='form-control variable-input min' id='" + min_label+ "'>";

                                    str += "<label for='"+max_label+"'>";
                                    str += "Max";
                                    str += "</label>";
                                    str += "<input type='number' class='form-control variable-input max' id='"+max_label+"'>";
                                    
                                    str += "</div";
                                }

                                return str;
                            }
                        }
                    })
                    .each(function(d, i){
                        if (!(d.key == 'index-label')){
                            if (data.stats && d3.select(this.parentNode).datum().key == 'variable'){
                                let data_min = data.stats.min[column_tuples[i]];
                                let data_max = data.stats.max[column_tuples[i]];

                                d3.select(this).select("input.min").property("value",data_min);
                                d3.select(this).select("input.max").property("value",data_max);
                            }
                        }
                    });

        // let subjects = d3.select("#session_list_table tbody").selectAll("tr")
        //     .data(d3.entries(data.experiment_data), function(d){return d.key;});
        let entries = d3.select("#session_list_table tbody").selectAll("tr")
            .data(d3.entries(entry_data), function(d){return d.key});

        // Remove rows for excluded entries
        entries.exit().remove();

        // Create rows for any new entries
        entries.enter()
                .append("tr")
                    .classed("participant-data", true)
                    .attr("id", function(d){
                        return "entry-"+d.key;
                    })
                .selectAll("td")
                    .data(function(d) {
                        return [{"key":"index-label","value":d.key}].concat(d3.entries(d.value));
                    }).enter()
                        .append("td")
                            .html(function(d,i) {
                                // if (d.key.match(/exclude/)){
                                //     let val = "<input type='checkbox' class='exclude-session-btn'";
                                //     if (d.value=="true") {
                                //         val += " checked";
                                //     }
                                //     val += ">";
                                //     return val
                                // } else {
                                    let val = d.value;
                                    if (d.key == "index-label"){
                                        val += "<div class='text-danger'><button type='button' class='subject exclude-session-btn btn btn-danger btn-sm' id='exclude-"+d.value+"'>Exclude</button></div>";
                                    }
                                    return val;
                                // }
                            })
                            .attr("class", function(d,i){
                                if (i) {
                                    return parseColumnTuple(d.key).reduce((outstr,d) => outstr+" "+d);
                                } else {
                                    return "text-primary freeze-pane index";
                                }
                            });

        // Attach event handlers
        d3.selectAll(".subject.exclude-session-btn").on("click", excludeSession);
        d3.selectAll(".variable-input").on("change", updateStatsHighlighting);
    };

    core.populateTable = function(data){
        // Create our basic table
        if (d3.select("#session_list_table").select("table").empty()){
            var table = d3.select("#session_list_table").append("table").attr("class","reporting table table-striped table-bordered table-sm"),
                thead = table.append("thead").attr("class","reporting"),
                tbody = table.append("tbody").attr("class","reporting");            
        } else {
            var thead = d3.select("#session_list_table thead");
            var tbody = d3.select("#session_list_table tbody");
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
        let entries = d3.select("#session_list_table tbody").selectAll("tr")
            .data(data, function(d){
                if (d.id != undefined){
                    return d.id;
                } else if (d.session_id != undefined){
                    return d.session_id;
                }
            });

        // Remove rows for removed entries
        entries.exit().remove();    

        // Create rows for any new entries        
        entries.enter()
            .append("tr")
                .attr("class", function(d){
                    let base_class = "session-data";
                    
                    if (d.meta && d.meta.all_completed) base_class += " session-all-complete";
                    
                    return base_class
                })
                .attr("id", function(d){
                    return "session-"+d.id;
                })
            .selectAll("td")
                .data(function(d){
                    return d3.entries(d).filter(function(d) {return d.key != "meta"})
                })
                .enter()
                .append("td")
                    .html(function(d){
                        if (d.key == 'subjects'){
                            return "<table class='subject-info'></table>"

                        } else if (d.key == 'id'){
                            let val = d.value;

                            val += "<div class='text-danger'><button type='button' class='session exclude-session-btn btn btn-danger btn-sm' id='exclude-"+d.value+"'>Exclude</button></div>";

                            return val

                        } else if (d.key == 'files'){
                            let session_id = d3.select(this.parentElement).datum().id;
                            let val = "<button type='button' class='btn btn-outline-info attach-file-btn' id='attach-file-"+session_id+"' data-toggle='modal' data-target='#attachFileModal' data-session='"+session_id+"'>Attach File</button>";;

                            val += "<div>"+d.value+"</div>";

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

        entries.select("table.subject-info").selectAll('tr')
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

        // Attach callbacks
        $(".session.exclude-session-btn").on("click", excludeSession);
        $(".attach-file-btn").on("click", function(){
            // Set the session ID on the modal
            document.querySelector(this.dataset.target).dataset.session = this.dataset.session;
        });

    }

    core.fetchAttachFileForm = function(ev){
        var session_id = ev.dataset.session;
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