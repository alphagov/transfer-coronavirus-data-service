// https://github.com/boto/boto3/issues/1149

load_s3upload_js();


function load_s3upload_js() {
  console.log("Loaded s3upload.js");

  var x = document.getElementById("upload_submit");
  if (x != null) {
    x.addEventListener('click', function(e) { upload_submit_click(this, e); });
  }

  var fs = get_file_settings()
  if (fs !== false) {
    fs.file_location.addEventListener('change', filename_change);
    fs.filename.addEventListener('keyup', filename_change);
    fs.file_ext.addEventListener('change', filename_change);
    filename_change();
  }
}


function get_file_settings() {
  var file_location = document.getElementById("file_location");
  if (file_location == null) {
    return false;
  }

  var filename = document.getElementById("filename");
  var file_ext = document.getElementById("file_ext");

  return {
    "file_location": file_location,
    "filename": filename,
    "file_ext": file_ext
  }
}


function filename_change() {
  var fs = get_file_settings()
  if (fs !== false) {
    let flv = fs.file_location.value;
    let cds = current_datetime_string();
    let fnv = fs.filename.value;
    if (fnv.trim() == "") {
      fnv = "{file name}"
    }
    let fev = fs.file_ext.value;

    var new_filename_display = "web-app-upload/" + flv + "/" + cds + "_" + fnv.trim() + "." + fev;

    var dfp = document.getElementById("dynamic_file_path");
    dfp.innerText = new_filename_display;
  }
}

function current_datetime_string() {
  const now = new Date();
  let y = now.getFullYear();
  let m = pad((now.getMonth() + 1), 2);
  let d = pad(now.getDate(), 2);
  let h = pad(now.getHours(), 2);
  let min = pad(now.getMinutes(), 2);
  let sec = pad(now.getSeconds(), 2);
  return y + m + d + "_" + h + min + sec;
}

function pad(n, width, z) {
  z = z || '0';
  n = n + '';
  return n.length >= width ? n : new Array(width - n.length + 1).join(z) + n;
}

// use the hidden filepathtoupload as the presignedurl
function upload_submit_click(s, e) {
  e.preventDefault();

  var form_files = document.getElementById("file").files;
  if (form_files.length != 1) {
    alert("Please choose a file to upload.");
    return false;
  }

  uploading_panel = document.getElementById("uploading_panel");
  uploading_panel.classList.remove("hidden");

  uploading_panel = document.getElementById("upload_panel");
  uploading_panel.classList.add("hidden");

  start_upload();

  return false;
}

function upload_complete(result) {
  document.getElementById("upload_success").classList.remove("hidden");
  document.getElementById("uploading_spinner").classList.add("hidden");
}

function upload_failed(result) {
  document.getElementById("upload_failure").classList.remove("hidden");
  document.getElementById("uploading_spinner").classList.add("hidden");
}

async function start_upload() {
  await ajax_file_upload();
}

function ajax_file_upload() {
  return new Promise(function() {
    var form_files = document.getElementById("file").files;
    var form_file_to_upload;

    if (form_files.length == 1) {
      form_file_to_upload = form_files[0];
    }

    let req = new XMLHttpRequest();
    let formData = new FormData();

    var hidden_params = document.getElementsByClassName('upload_form_post_param');
    for (var i = 0; i < hidden_params.length; i++) {
      form_key = hidden_params[i].name;
      form_val = hidden_params[i].value;
      formData.append(form_key, form_val);
    }

    formData.append("file", form_file_to_upload);

    var action_url = document.getElementById("upload_form").action;
    req.open("POST", action_url);

    req.onload = function () {
        if (this.status >= 200 && this.status < 300) {
            upload_complete(req.response);
        } else {
            upload_failed({
                status: this.status,
                statusText: req.statusText
            });
        }
    };
    req.onerror = function () {
        upload_failed({
            status: this.status,
            statusText: req.statusText
        });
    };

    req.send(formData);
  });
}
