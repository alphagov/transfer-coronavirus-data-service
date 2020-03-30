const const_bucketname = "backend-data-access-test";
const const_region = "eu-west-2";
const const_userpoolid = "eu-west-2_pjM9bY9eD";
const const_clientid = "2s4ccdrs0urfa4lih383m7tmk5"
const const_appwebdomain = "cyber-manual-test-73hdxjhsy2jmap.auth.eu-west-2.amazoncognito.com";
const const_identitypoolid = "eu-west-2:db6b32a9-84eb-439e-b9d3-a797141d2fbf";

AWS.config.logger = console;

function setUpAWSCreds(result) {
  var logins = {};
  logins['cognito-idp.'+const_region+'.amazonaws.com/'+const_userpoolid] = result.getIdToken().getJwtToken();

  AWS.config.credentials = new AWS.CognitoIdentityCredentials({
      IdentityPoolId: const_identitypoolid,
      Logins: logins
  });
}

var masterAuth = false;

// Operations when the web page is loaded.
function mainOnLoad() {
  // Initiatlize CognitoAuth object
  initCognitoSDK();
  document.getElementById("signInButton").addEventListener("click", function() {
    userButton();
  });

  document.getElementById("getFilesButton").addEventListener("click", function() {
    startLoading();
    window.setTimeout(handleRequest, 100);
  });

  var curUrl = window.location.href;
  masterAuth.parseCognitoWebResponse(curUrl);
}

// Perform user operations.
function userButton() {
  var state = document.getElementById('signInButton').innerText;
  if (state === "Sign In") {
    masterAuth.getSession();
  } else {
    masterAuth.signOut();
  }
}

// Operations when signed out.
function showSignedOut() {
  document.getElementById('signInButton').innerText = "Sign In"
  document.getElementById("getFilesButton").style.display = 'none';
  document.getElementById("userinfo").style.display = 'none';
  clearFileList();
}

function clearFileList() {
  var viewer = document.getElementById("viewer");
  viewer.innerHTML = '';
}

function startLoading() {
  console.log("Started loading...")
  document.getElementById("showwhenloading").style.display = 'block';
  document.getElementById("hidewhenloading").style.display = 'none';
}

function stopLoading() {
  console.log("Stopped loading...")
  document.getElementById("showwhenloading").style.display = 'none';
  document.getElementById("hidewhenloading").style.display = 'block';
}

function handleRequest() {
  clearFileList();
  setUpAWSCreds(masterAuth.getCachedSession());
  listObjects();
  window.setTimeout(stopLoading, 100);
}


// Initialize a cognito auth object.
function initCognitoSDK() {
  var authData = {
    ClientId : const_clientid, // Your client id here
    AppWebDomain : const_appwebdomain, // Exclude the "https://" part.
    TokenScopesArray : ['openid','email','phone'],
    RedirectUriSignIn : window.location.protocol + "//" + window.location.host + window.location.pathname,
    RedirectUriSignOut : window.location.protocol + "//" + window.location.host + window.location.pathname,
    UserPoolId : const_userpoolid,
    AdvancedSecurityDataCollectionFlag : false
  };

  masterAuth = new AmazonCognitoIdentity.CognitoAuth(authData);

  AWS.config.region = const_region; // Region

  // You can also set state parameter
  // auth.setState(<state parameter>);
  masterAuth.userhandler = {
    onSuccess: function(result) {
      startLoading();
      document.getElementById('signInButton').innerText = "Sign Out";
      document.getElementById("getFilesButton").style.display = 'block';
      document.getElementById("userinfo").style.display = 'block';
      window.setTimeout(addSessionDetails(), 1000);
    },
    onFailure: function(err) {
      alert("Error! " + err);
    }
  };
}


function addSessionDetails() {
  var user = masterAuth.getCachedSession().idToken.payload["cognito:username"];
  var email = masterAuth.getCachedSession().idToken.payload.email;
  document.getElementById("userspan").innerText = user;
  document.getElementById("emailspan").innerText = email;
  stopLoading();
}


// List the photo albums that exist in the bucket.
function listObjects() {

  var s3 = new AWS.S3({
    apiVersion: "2006-03-01",
    params: { Bucket: const_bucketname }
  });

  //var sub = masterAuth.getCachedSession().accessToken.payload.sub;
  //prefix = 'cognito/' + AWS.config.credentials.identityId + "/";
  //prefix = 'cognito/' + const_region + ':' + sub + "/";
  prefix = "cognito/103495720024:ollie/";
  console.log("Attempting to get objects from: "+ prefix);

  s3.listObjects({
    Prefix: prefix
  }, function(err, data) {
    if (err) {
      return alert('There was an error listing your bucket: ' + err.message);
    } else {
      var counter = 0;

      var itemCount = data.Contents.length;
      for (i = 0; i < data.Contents.length; i++) {
        var obj = data.Contents[i];
        var key = obj.Key;
        if (! key.endsWith("/")) {
          counter ++;

          const signedUrlExpireSeconds = 60 * 5;
          var url = s3.getSignedUrl('getObject', {
              Bucket: const_bucketname,
              Key: data.Contents[i].Key,
              Expires: signedUrlExpireSeconds
          });

          var friendlyKey = key.replace(prefix, "");

          var d = document.createElement('div');

          var a = document.createElement('a');
          var linkText = document.createTextNode(friendlyKey);
          a.appendChild(linkText);
          a.title = friendlyKey;
          a.href = url;
          a.target = "_blank";
          d.appendChild(a);

          var s = document.createElement('span');
          s.innerText = " (" + obj.Size + " bytes)";
          d.appendChild(s)

          var viewer = document.getElementById("viewer");
          viewer.appendChild(d);
        }
      }

      var p = document.createElement('p');
      p.innerHTML = "Found "+counter+" file(s) available:";
      viewer.insertBefore(p, viewer.childNodes[0]);
    }
  });

}
