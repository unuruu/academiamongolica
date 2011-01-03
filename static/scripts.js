$(document).ready(function() {              
    $("#lookup").bind("keydown", function(event) {
        if (event.keyCode == 13) {
            var keyword = $.trim($("#lookup").val());
            location.href = "/" + keyword;
        }
    });
    
    $("#lookup").autocomplete({ 
        serviceUrl: "/lookup",
        deferRequestBy: 0,
        noCache: false
    });
    
    $(".translation").click(function() {
        $(".translation").css("background", "#fff");
        $(this).css("background", "#c5cfe1");
        $("#comments_window").attr("src", "comments/" + $(this).attr("id"));
    });
});

function vote(translation,val) {
    $.ajax({
        url: "/vote",
        type: "post",
        data: "translation=" + translation +
            "&val=" + parseInt(val,10),
        success: function(data) {
            if (data == "NOTLOGGEDIN") {
                alert("Та системд нэвтрээгүй байна");
            } else if (data == "DUPLICATE") {
                alert("Та адилхан санал өгсөн байна");
            } else {
                ret = JSON.parse(data);
                $("#" + ret.translation).find("span").text(ret.vote);
            }
        }
    });
} 