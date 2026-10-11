document.addEventListener("DOMContentLoaded", function () {
  const passwordToggles = document.querySelectorAll(".password-toggle");

  passwordToggles.forEach(function (button) {
    button.addEventListener("click", function () {
      const targetId = button.getAttribute("data-target");
      const input = document.getElementById(targetId);

      if (!input) {
        return;
      }

      if (input.type === "password") {
        input.type = "text";
        button.textContent = "Hide";
        button.setAttribute("aria-label", "Hide password");
      } else {
        input.type = "password";
        button.textContent = "Show";
        button.setAttribute("aria-label", "Show password");
      }
    });
  });

  const registerForm = document.getElementById("registerForm");

  if (registerForm) {
    registerForm.addEventListener("submit", function () {
      const button = document.getElementById("registerButton");

      if (button) {
        button.textContent = "Creating Account...";
        button.disabled = true;
      }
    });
  }
});
