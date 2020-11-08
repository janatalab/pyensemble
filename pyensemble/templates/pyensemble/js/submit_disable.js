    $('#question-form').submit(function(){
        $("input[name='submit']").attr({"disabled": true});
        return true;
    });
    