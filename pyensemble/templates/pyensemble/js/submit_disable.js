    $('#question-form').submit(function(e){
        if ($("input[name='submit']").attr("attempted") == true){
            e.preventDefault();
        } else {
            $("input[name='submit']").attr("attempted",'true');
        }
    });
