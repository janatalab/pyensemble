<script type="text/javascript">
    $(function(){
        $(".editor-form").on('submit',function(ev){
            ev.preventDefault();
            submitForm($(".editor-form"));
        });
    });
</script>