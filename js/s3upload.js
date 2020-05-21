// https://github.com/boto/boto3/issues/1149

load_s3upload_js();

function s3_upload_console_log(message) {
    if (typeof console == "undefined") {
        console.log(message);
    }
}

function load_s3upload_js() {
    s3_upload_console_log("Loaded s3upload.js");

    var x = document.getElementById("upload_submit");
    if (x != null) {
        x.addEventListener('click', function(e) { upload_submit_click(this, e); });
    }

    var fs = get_file_settings()
    if (fs !== false) {
        fs.file_location.addEventListener('change', file_name_change);
        fs.file_name.addEventListener('keyup', file_name_change);
        fs.file_ext.addEventListener('change', file_name_change);
        file_name_change();
    }
}


function get_file_settings() {
    var file_location = document.getElementById("file_location");
    if (file_location == null) {
        return false;
    }

    var file_name = document.getElementById("file_name");
    var file_ext = document.getElementById("file_ext");

    return {
        "file_location": file_location,
        "file_name": file_name,
        "file_ext": file_ext
    }
}


function file_name_change() {
    var fs = get_file_settings()
    if (fs !== false) {
        var flv = fs.file_location.value;
        var cds = current_datetime_string();
        var fnv = fs.file_name.value;
        if (fnv.trim() == "") {
            fnv = "{file name}"
        }
        var fev = fs.file_ext.value;

        var new_file_name_display = flv + "/" + cds + "_" + fnv.trim() + "." + fev;

        var dfp = document.getElementById("dynamic_file_path");
        dfp.innerText = new_file_name_display;
    }
}

function current_datetime_string() {
    var now = new Date();
    var y = now.getFullYear();
    var m = pad((now.getMonth() + 1), 2);
    var d = pad(now.getDate(), 2);
    var h = pad(now.getHours(), 2);
    var min = pad(now.getMinutes(), 2);
    var sec = pad(now.getSeconds(), 2);
    return y + m + d + "_" + h + min + sec;
}

function pad(n, width, z) {
    z = z || '0';
    n = n + '';
    return n.length >= width ? n : new Array(width - n.length + 1).join(z) + n;
}

// use the hidden filepathtoupload as the presignedurl
function upload_submit_click(element, event) {

    var do_default_html_form_submit = true;

    //Detect browser support for CORS
    if ('withCredentials' in new XMLHttpRequest()) {
        /* supports cross-domain requests */
        event.preventDefault();

        var form_files = document.getElementById("file").files;
        if (form_files.length != 1) {

            alert("Please choose a file to upload.");

        } else {

            uploading_panel = document.getElementById("uploading_panel");
            uploading_panel.classList.remove("hidden");

            uploading_panel = document.getElementById("upload_panel");
            uploading_panel.classList.add("hidden");

            start_upload();

        }
        do_default_html_form_submit = false;
    }
    /*
    // Investigate which browsers this will add support for
    // and how to implement
    else if(typeof XDomainRequest !== "undefined"){
        //Use IE-specific "CORS" code with XDR
        s3_upload_console_log("CORS supported (XDR)");
    */
    else {
        alert(
            "Please note: We can't detect the upload status for this browser. \n" +
            "Please wait for an email confirmation of your file upload " +
            "before leaving this page."
        )
    }


    return do_default_html_form_submit;
}

function upload_complete(result) {
    document.getElementById("upload_success").classList.remove("hidden");
    document.getElementById("uploading_spinner").classList.add("hidden");
}

function upload_failed(result) {
    document.getElementById("upload_failure").classList.remove("hidden");
    document.getElementById("uploading_spinner").classList.add("hidden");
}

//async function start_upload() {
//  await ajax_file_upload();
//}

function start_upload() {
    ajax_file_upload();
}

function get_http_object() {
    var req;
    if(window.ActiveXObject) { req = new ActiveXObject('Microsoft.XMLHTTP'); }
    else if(window.XMLHttpRequest) { req = new XMLHttpRequest(); }
    return req
}

function ajax_file_upload() {
    var form_files = document.getElementById("file").files;
    var form_file_to_upload;

    if (form_files.length == 1) {
      form_file_to_upload = form_files[0];
    }

    var req = get_http_object()
    var formData = new FormData();

    var hidden_params = document.getElementsByClassName('upload_form_post_param');
    for (var i = 0; i < hidden_params.length; i++) {
      form_key = hidden_params[i].name;
      form_val = hidden_params[i].value;
      formData.append(form_key, form_val);
    }

    formData.append("file", form_file_to_upload);

    var action_url = document.getElementById("upload_form").action;
    req.open("POST", action_url, true);
    req.onreadystatechange = function() {
        if(this.readyState == 4) {
            var result = this.responseText;
            if (req.status >= 200 && this.status < 300) {
                upload_complete(result);
            } else {
                upload_failed({
                    status: this.status,
                    statusText: this.statusText
                });
            }
        }
    }

    req.send(formData);
}