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
  var form_file_to_upload;

  if (form_files.length != 1) {
    alert("Please choose a file to upload.");
    return false;
  } else {
    form_file_to_upload = form_files[0];
  }

  let req = new XMLHttpRequest();

  req.addEventListener("load", upload_complete);
  req.addEventListener("error", upload_failed);

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
  //req.setRequestHeader("Content-type", "multipart/form-data");
  req.send(formData);

  return false;
}

function upload_complete(e) {
  console.log(e);
  console.log(this.response);
  console.log(this.status);
  console.log(this.statusText);
}

function upload_failed(e) {
  console.log(e);
}
