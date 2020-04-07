// https://github.com/boto/boto3/issues/1149

load_s3upload_js();


function load_s3upload_js() {
  console.log("Loaded s3upload.js");
  var x = document.getElementById("upload_submit");
  x.addEventListener('click', function(e) { upload_submit_click(this, e); });
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

  console.log("hiding upload_panel, showing uploading_panel");

  start_upload();

  return false;
}

function upload_complete(result) {
  console.log("upload_complete");
  console.log(result);
  document.getElementById("upload_success").classList.remove("hidden");
  document.getElementById("uploading_spinner").classList.add("hidden");
}

function upload_failed(result) {
  console.log("upload_failed");
  console.log(result);
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
