document.addEventListener("DOMContentLoaded", function () {
  const guestInput = document.getElementById("guestCount");

  if (!guestInput) {
    return;
  }

  const maxGuests = parseInt(guestInput.getAttribute("max"), 10);

  if (Number.isNaN(maxGuests)) {
    return;
  }

  guestInput.addEventListener("input", function () {
    const value = parseInt(this.value, 10);

    if (!Number.isNaN(value) && value > maxGuests) {
      this.setCustomValidity(`You can enter maximum ${maxGuests} guests.`);
    } else {
      this.setCustomValidity("");
    }
  });
});
