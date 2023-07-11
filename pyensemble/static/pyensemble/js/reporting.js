// reporting.js

// $(function() {
window.PyEnsemble.reporting = (function(){
    var core = {};

    core.urls = JSON.parse(document.getElementById('reporting-urls').textContent);

    core.callbacks = {
        'attach-file-modal-post-submit': onAttachedFile,
    };

    core.currentAnalysisLevel = undefined;

    core.resetCurrentSelections = function(){
        core.currentSelections = {
            study: undefined,
            experiment: undefined,
            subject: undefined,
            session: undefined,
        };

        $("#secondary-navbar").addClass("d-none");

        $("#summary_section").html("");
        $("#summary_section").addClass("d-none");

        $("#session_list_table").html("");
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

        // Set our summary and session urls
        $("#summary-nav-link").attr({href: core.urls[level+'-summary']})
        $("#sessions-nav-link").attr({href: core.urls[level+'-sessions']})

        $("#secondary-navbar").removeClass("d-none");

        var url = "";
    }

    $('.selectpicker').selectpicker()
        .on('changed.bs.select', onChangedSelection);

    $(".analysis-item").on('click', onAnalysisRequest);

    function onAnalysisRequest(ev){
        ev.stopImmediatePropagation();
        ev.preventDefault();

        // Get our selected experiment
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
        d3.selectAll(".session-data").each(function(d){
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
        populateTable(data);
    }
    
    function populateTable(data){
        // Get the data that we will be entering into the table
        var table_entry_data = undefined;

        if (data.type == "study_data"){
            table_entry_data = data.experiment_data;

        } else if (data.type == "experiment_data"){
            table_entry_data = data.session_data;
        }

        // If we have no data to display, state as much and exit
        if (!table_entry_data){
            let ss = $("#summary_section");
            ss.html("No session data available");
            ss.removeClass("d-none");
            return
        }

        // Get our column label information, keeping in mind that we can have multiple levels of columns
        var column_info = getColumnInfo(Object.values(table_entry_data)[0]);

        function getColumnInfo(entry_data_template){
            // Extract the column labels
            let column_tuples = Object.keys(entry_data_template);

            // Build the column header
            let level_items = column_tuples.map(parseColumnTuple);

            let num_levels = level_items[0].length;

            // Initialize our levels array
            let levels = [];

            for (let l=0; l<num_levels; l++){
                levels[l] = {}
                
                levels[l].key = num_levels > 1 ? l ? "variable" : "experiment" : "variable";
                levels[l].value = level_items.map(function(d){return d[l]}).filter(d=>d!="meta");
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

            let column_info = {
                column_tuples: column_tuples,
                levels: levels,
                num_levels: num_levels,
                level_items: level_items,
            };

            return column_info
        };

        // Create our basic table
        if (d3.select("#session_list_table").select("table").empty()){
            var table = d3.select("#session_list_table").append("table").attr("class","reporting table table-striped table-bordered table-sm"),
                thead = table.append("thead").attr("class","reporting"),
                tbody = table.append("tbody").attr("class","reporting");            
        } else {
            var thead = d3.select("#session_list_table thead");
            var tbody = d3.select("#session_list_table tbody");
        }

        // Attach data to column header rows
        let header_rows = thead.selectAll("tr")
            .data(column_info.levels, function(d){return d.key;});

        // Remove header rows, e.g. if switching from study to experiment
        header_rows.exit().remove();

        // Add our column headers
        let column_headers = header_rows.enter().append("tr").selectAll("th")
            .data(function(d){return d.value;});

        column_headers.enter()
            .append("th")
                .attr("rowspan", function(d){
                    return d.key=="index-label" ? column_info.num_levels : 1;
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
                            if (column_info.num_levels > 1){
                                retval = column_info.level_items[i][0] + " " + d;
                            } else {
                                if (i == 0) retval = "freeze-pane index";
                                if (d == "notes") retval = "reporting-notes-col";

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
                                let experiment_str = column_info.num_levels > 1 ? column_info.level_items[i][0]+"-" : "";

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
                            let data_min = data.stats.min[column_info.column_tuples[i]];
                            let data_max = data.stats.max[column_info.column_tuples[i]];

                            d3.select(this).select("input.min").property("value",data_min);
                            d3.select(this).select("input.max").property("value",data_max);
                        }
                    }
                });

        // Remove any deleted columns
        column_headers.exit().remove();

        // Add session entries
        let entries = d3.select("#session_list_table tbody").selectAll("tr")
            .data(d3.entries(table_entry_data), function(d){return d.key});

        // Remove rows for excluded entries
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
                    return "entry-"+d.key;
                })
            .selectAll("td")
                .data(function(d) {
                    return [{"key":"index-label","value":d.key}].concat(d3.entries(d.value).filter(function(d){return d.key != "meta"}));
                }).enter()
                    .append("td")
                        .html(function(d,i) {
                            let val = d.value;

                            if (d.key == "index-label"){
                                val += "<div class='text-danger'><button type='button' class='session exclude-session-btn btn btn-danger btn-sm' id='exclude-"+d.value+"'>Exclude</button></div>";

                            } else if (d.key == 'subject_session_data'){
                                return "<table class='subject-info'></table>"

                            } else if (d.key == 'files'){
                                let session_id = d3.select(this.parentElement).datum().key;
                                
                                val = "<button type='button' class='btn btn-outline-info attach-file-btn' id='attach-file-"+session_id+"' data-toggle='modal' data-target='#attachFileModal' data-session='"+session_id+"'>Attach File</button>";;

                                val += "<div>"+d.value+"</div>";
                            } else if (d.key == "last_response"){
                                if (d.value){
                                    return Object.values(d.value).join(', ')
                                } else {
                                    return "No responses"
                                }
                            }

                            return val;
                        })
                        .attr("class", function(d,i){
                            let class_str = "align-middle";

                            if (i) {
                                return parseColumnTuple(d.key).reduce((outstr,d) => class_str + " " + d);
                            } else {
                                return class_str + " text-primary freeze-pane index";
                            }
                        });


        entries.select("table.subject-info").selectAll('tr')
            .data(function(d){
                return d3.entries(d.value.subject_session_data)
            }, function(s){
                return s.key
            })
            .enter()
            .append("tr")
                .selectAll("td")
                .data(function(d){
                    return d3.entries(d.value)
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
        var url = core.urls['attach-file'];

        // Get our session ID
        core.currentSelections.session = ev.dataset.session;

        $.ajax({
            url: url,
            type: 'GET',
            dataType: "html",        
            data: core.currentSelections,
            success: function(response){
                $(ev).find(".modal-body").html(response);
                $(ev).find("form").attr({action:url});
            },
            error: function(response){
                alert('Unable to fetch file attachment form ...')
            }
        });        
    }

    function onAttachedFile(data){
        // Update the files table cell for this session
    }

    return core
})();
