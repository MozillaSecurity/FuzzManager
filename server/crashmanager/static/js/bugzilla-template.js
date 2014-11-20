$(document).ready( function() {
    $('#template').change(function(){
        url = window.location.href

        if (url.indexOf("template=") > -1) {
            window.location = url.replace(/(\?|&)template=\d+/g, "\$1" + "template=" + $(this).val());
        } else {
            if (url.indexOf("?") > -1) {
                window.location = url + "&template=" + $(this).val()
            } else {
                window.location = url + "?template=" + $(this).val()
            }
        }
    });
});
