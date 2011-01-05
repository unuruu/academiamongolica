$(document).ready(function() {    
    $("#lookup").autocomplete({ 
        serviceUrl: "/lookup",
        deferRequestBy: 0,
        noCache: false
    });
    
    $(".translation").click(function() {
        $(".translation").css("background", "#fff");
        $(this).css("background", "#f0f0f0");
        $("#comments_window").attr("src", "comments/" + $(this).attr("id"));
        $("#updates").hide();
        $("#comments").fadeIn();
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