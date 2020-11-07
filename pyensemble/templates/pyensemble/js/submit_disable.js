    $('#question-form').submit(function(){
        $("input[name='submit']").attr({"value":"Please wait","disabled": true});
        return true;
    });