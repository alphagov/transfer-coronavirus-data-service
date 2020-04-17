document.body.className = ((document.body.className) ? document.body.className + ' js-enabled' : 'js-enabled');
window.GOVUKFrontend.initAll();

load_is_la_radio_js();
load_account_switch_js();

function load_is_la_radio_js() {
  console.log("load_is_la_radio_js");
  var x = document.getElementsByName("is-la-radio");
  var i;
  for (i = 0; i < x.length; i++) {
    if (x[i].type == "radio" && x[i].checked) {
      is_la_switch(x[i].value);
    }
    x[i].addEventListener('change', function() { is_la_switch(this.value); });
  }
}

function load_account_switch_js() {
  console.log("load_account_switch_js");
  var x = document.getElementById("account-select");
  if (x != null) {
    x.addEventListener('change', function() { account_switch(this.value); });
    account_switch(x.value)
  }
}

function account_switch(s) {
  var is_admin = (s.indexOf("admin-") === 0)
  if (is_admin) {
    document.getElementById("standard-user-inputs").classList.add("hidden");
  } else {
    document.getElementById("standard-user-inputs").classList.remove("hidden");
  }
}

function is_la_switch(s) {
  var is_la = (s === "yes");
  if (is_la) {
    document.getElementById("la_cond").removeAttribute("disabled");
    document.getElementById("la_cond").setAttribute("checked", "checked")
    document.getElementById("la_cond").click();
    document.getElementById("conditional-la_cond").classList.remove("govuk-radios__conditional--hidden");

    document.getElementById("other_cond").removeAttribute("aria-expanded")
    document.getElementById("other_cond").checked = false;
    document.getElementById("other_cond").setAttribute("disabled", "disabled");
    document.getElementById("conditional-other_cond").classList.add("govuk-radios__conditional--hidden");
  } else {
    document.getElementById("la_cond").removeAttribute("aria-expanded")
    document.getElementById("la_cond").checked = false;
    document.getElementById("la_cond").setAttribute("disabled", "disabled");
    document.getElementById("conditional-la_cond").classList.add("govuk-radios__conditional--hidden");

    document.getElementById("other_cond").removeAttribute("disabled");
    document.getElementById("other_cond").setAttribute("checked", "checked")
    document.getElementById("other_cond").click();
    document.getElementById("conditional-other_cond").classList.remove("govuk-radios__conditional--hidden");
  }
}
