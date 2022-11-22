<script type="text/javascript">
    $(function(){
        $(".editor.form-actions button").on('click',function(ev){
            ev.stopImmediatePropagation();
            ev.preventDefault();
            submitForm($(".editor-form"));
        });
    });
</script>
