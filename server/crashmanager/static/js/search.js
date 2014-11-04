$(document).ready( function() {
    $("#search").focus( function() {
        if ( $(this).val()=="Search for Crash") {
            $(this).val('');
        } 
    });

    $("#search").blur( function() {
        if ( $(this).val()=="") {
            $(this).val('Search for Crash');
        } 
    });
});
