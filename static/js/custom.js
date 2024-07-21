function setCookie(cookieName, value) {
  document.cookie = `${cookieName}=${value}; path=/;`;
}

function getCookie(cookieName) {
  const name = `${cookieName}=`;
  const decodedCookie = decodeURIComponent(document.cookie);
  const cookieArray = decodedCookie.split(";");

  for (let i = 0; i < cookieArray.length; i++) {
    let cookie = cookieArray[i].trim();

    if (cookie.indexOf(name) == 0) {
      if (cookie.substring(name.length, cookie.length) == "false") return false;
      else return true;
    }
  }
  return null;
}

if (getCookie("eventMenu") == null) {
  setCookie("eventMenu", "false");
}

if (getCookie("faceMenu") == null) {
  setCookie("faceMenu", "false");
}

document.addEventListener("alpine:init", () => {
  Alpine.data("eventMenu", () => ({
    eventOpen: getCookie("eventMenu"),
    eventToggle() {
      this.eventOpen = !this.eventOpen;
      setCookie("eventMenu", this.eventOpen);
      console.log(this.eventOpen);
    },
    faceOpen: getCookie("faceMenu"),
    faceToggle() {
      this.faceOpen = !this.faceOpen;
      setCookie("faceMenu", this.faceOpen);
      console.log(this.faceOpen);
    },
  }));
});

document.addEventListener("DOMContentLoaded", () => {
  console.log("Ready!");

  // Validate password
  // $("#submit-button").click(function (event) {
  //   var pass = $("#pass").val();
  //   var confirmation = $("#confirmation").val();
  //   var regex = /^(?=.*[0-9])(?=.*[!@#$%^&*])[a-zA-Z0-9!@#$%^&*]{8,32}$/;
  //   if (!pass.match(regex)) {
  //     event.preventDefault();
  //     alert(
  //       "Password must be 8-32 characters long and contain at least one number and one special character."
  //     );
  //   } else if (pass != confirmation) {
  //     event.preventDefault();
  //     alert(
  //       "Password and confirmation do not match. Please re-enter them and try again."
  //     );
  //   }
  // });

  $(".nameInput").on("focusout", function () {
    var newName = $(this).val();
    var faceId = $(this).data("face-id"); // Retrieve the face ID from the data attribute
    var csrfToken = $(this).data("csrf-token"); // Retrieve the face ID from the data attribute
    
    $.ajax({
      type: "POST",
      url: "/update_name",
      data: { name: newName, face_id: faceId, csrf_token: csrfToken }, // Send both the new name and the face ID to the server
      success: function (response) {
        // console.log(response);
      },
      error: function (error) {
        console.log(error);
      },
    });
  });
});
