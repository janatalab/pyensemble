<script type="text/javascript">
    $(function(){
        $(".editor-form").on('submit',function(ev){
            ev.stopImmediatePropagation();
            ev.preventDefault();
            submitForm($(".editor-form"));
        })
    })
</script>