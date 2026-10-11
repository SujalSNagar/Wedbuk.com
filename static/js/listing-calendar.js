document.addEventListener("DOMContentLoaded", function () {
  const modal = document.getElementById("availabilityModal");

  const modalOverlay = document.getElementById("availabilityModalOverlay");

  const modalClose = document.getElementById("availabilityModalClose");

  const openButton = document.querySelector(".check-availability-button");

  const calendar = document.getElementById("bookingCalendar");

  const calendarPrev = document.getElementById("calendarPrev");

  const calendarNext = document.getElementById("calendarNext");

  const calendarMonthYear = document.getElementById("calendarMonthYear");

  const calendarDays = document.getElementById("calendarDays");

  const calendarDateInfo = document.getElementById("calendarDateInfo");

  const selectedRangeBox = document.getElementById("calendarSelectedRange");

  const selectedStartDate = document.getElementById("selectedStartDate");

  const selectedEndDate = document.getElementById("selectedEndDate");

  const selectedRangeDays = document.getElementById("selectedRangeDays");

  const selectedRangeStatus = document.getElementById("selectedRangeStatus");

  const continueBookingButton = document.getElementById(
    "continueBookingButton",
  );

  if (!modal || !openButton || !calendar || !calendarDays) {
    return;
  }

  // =====================================================
  // STATE
  // =====================================================

  let currentDate = new Date();

  currentDate.setDate(1);

  let availabilityPeriods = [];

  let blockedDates = new Set();

  let bookedDates = new Set();

  let rangeStart = null;

  let rangeEnd = null;

  let availabilityLoaded = false;

  // =====================================================
  // DATE HELPERS
  // =====================================================

  function pad(value) {
    return String(value).padStart(2, "0");
  }

  function formatDate(date) {
    return (
      date.getFullYear() +
      "-" +
      pad(date.getMonth() + 1) +
      "-" +
      pad(date.getDate())
    );
  }

  function parseDate(value) {
    const parts = value.split("-");

    return new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
  }

  function todayString() {
    return formatDate(new Date());
  }

  function displayDate(value) {
    return parseDate(value).toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  }

  function numberOfDays(start, end) {
    const first = parseDate(start);

    const last = parseDate(end);

    return Math.round((last.getTime() - first.getTime()) / 86400000) + 1;
  }

  // =====================================================
  // AVAILABILITY CHECK
  // =====================================================

  function isInsideAvailability(dateString) {
    return availabilityPeriods.some(function (period) {
      return dateString >= period.from && dateString <= period.until;
    });
  }

  function isAvailable(dateString) {
    // Past
    if (dateString < todayString()) {
      return false;
    }

    // Booked
    if (bookedDates.has(dateString)) {
      return false;
    }

    // Blocked
    if (blockedDates.has(dateString)) {
      return false;
    }

    // Outside vendor availability
    if (!isInsideAvailability(dateString)) {
      return false;
    }

    return true;
  }

  function isRangeAvailable(start, end) {
    let current = parseDate(start);

    const last = parseDate(end);

    while (current <= last) {
      const value = formatDate(current);

      if (!isAvailable(value)) {
        return false;
      }

      current.setDate(current.getDate() + 1);
    }

    return true;
  }

  // =====================================================
  // LOAD API
  // =====================================================

  async function loadAvailability() {
    const url = calendar.dataset.availabilityUrl;

    if (!url) {
      showError("Availability URL is missing.");

      return;
    }

    calendarDays.innerHTML = "";

    calendarDateInfo.textContent = "Loading availability...";

    try {
      const response = await fetch(url, {
        method: "GET",

        headers: {
          Accept: "application/json",
        },

        cache: "no-store",
      });

      /*
       * If Django returns 404/500/etc.,
       * show the actual HTTP status.
       */

      if (!response.ok) {
        const errorText = await response.text();

        console.error("Availability API error:", response.status, errorText);

        throw new Error("HTTP " + response.status);
      }

      const data = await response.json();

      console.log("Availability API:", data);

      availabilityPeriods = Array.isArray(data.availability_periods)
        ? data.availability_periods
        : [];

      blockedDates = new Set(
        Array.isArray(data.blocked_dates) ? data.blocked_dates : [],
      );

      bookedDates = new Set(
        Array.isArray(data.booked_dates) ? data.booked_dates : [],
      );

      availabilityLoaded = true;

      rangeStart = null;

      rangeEnd = null;

      updateRangeInformation();

      renderCalendar();
    } catch (error) {
      console.error("Unable to load availability:", error);

      showError("Unable to load booking availability.");
    }
  }

  // =====================================================
  // ERROR
  // =====================================================

  function showError(message) {
    calendarMonthYear.textContent = "Availability";

    calendarDays.innerHTML = `
            <div class="calendar-error">
                ${message}
            </div>
        `;

    calendarDateInfo.textContent = message;
  }

  // =====================================================
  // MODAL
  // =====================================================

  function openModal() {
    modal.classList.add("show");

    modal.setAttribute("aria-hidden", "false");

    document.body.style.overflow = "hidden";

    loadAvailability();
  }

  function closeModal() {
    modal.classList.remove("show");

    modal.setAttribute("aria-hidden", "true");

    document.body.style.overflow = "";
  }

  openButton.addEventListener("click", openModal);

  if (modalClose) {
    modalClose.addEventListener("click", closeModal);
  }

  if (modalOverlay) {
    modalOverlay.addEventListener("click", closeModal);
  }

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && modal.classList.contains("show")) {
      closeModal();
    }
  });

  // =====================================================
  // RENDER CALENDAR
  // =====================================================

  function renderCalendar() {
    if (!availabilityLoaded) {
      return;
    }

    const year = currentDate.getFullYear();

    const month = currentDate.getMonth();

    calendarMonthYear.textContent = currentDate.toLocaleDateString("en-IN", {
      month: "long",
      year: "numeric",
    });

    calendarDays.innerHTML = "";

    const firstDay = new Date(year, month, 1);

    const daysInMonth = new Date(year, month + 1, 0).getDate();

    const startingDay = firstDay.getDay();

    // Previous month filler

    const previousMonthLastDay = new Date(year, month, 0).getDate();

    for (let i = startingDay - 1; i >= 0; i--) {
      const date = new Date(year, month - 1, previousMonthLastDay - i);

      calendarDays.appendChild(createDay(date, true));
    }

    // Current month

    for (let day = 1; day <= daysInMonth; day++) {
      const date = new Date(year, month, day);

      calendarDays.appendChild(createDay(date, false));
    }

    // Next month filler

    const total = calendarDays.children.length;

    const remaining = total % 7 === 0 ? 0 : 7 - (total % 7);

    for (let day = 1; day <= remaining; day++) {
      const date = new Date(year, month + 1, day);

      calendarDays.appendChild(createDay(date, true));
    }
  }

  // =====================================================
  // CREATE DAY
  // =====================================================

  function createDay(date, otherMonth) {
    const value = formatDate(date);

    const button = document.createElement("button");

    button.type = "button";

    button.className = "calendar-day";

    button.textContent = date.getDate();

    button.dataset.date = value;

    if (otherMonth) {
      button.classList.add("other-month");

      button.disabled = true;

      return button;
    }

    // Past

    if (value < todayString()) {
      button.classList.add("past");

      button.disabled = true;

      return button;
    }

    // Booked

    if (bookedDates.has(value)) {
        button.classList.add("booked");
        button.disabled = true;
        button.title = "Booked";
    
        return button;
    }

    // Blocked

    if (blockedDates.has(value)) {
      button.classList.add("blocked");

      button.disabled = true;

      return button;
    }

    // Outside availability

    if (!isInsideAvailability(value)) {
      button.classList.add("blocked");

      button.disabled = true;

      return button;
    }

    // Available

    button.classList.add("available");

    // Selected range

    if (rangeStart && rangeEnd && value >= rangeStart && value <= rangeEnd) {
      button.classList.add("in-range");
    }

    if (value === rangeStart) {
      button.classList.add("range-start");
    }

    if (value === rangeEnd) {
      button.classList.add("range-end");
    }

    button.addEventListener("click", function () {
      handleDateClick(value);
    });

    return button;
  }

  // =====================================================
  // DATE CLICK
  // =====================================================

function handleDateClick(value) {

    if (!isAvailable(value)) {
        return;
    }


    // =====================================================
    // A COMPLETE RANGE ALREADY EXISTS
    // Clicking any available date starts a NEW range.
    // Example: 8–10 selected → click 9 → 9 becomes new start.
    // =====================================================

    if (rangeStart && rangeEnd) {

        rangeStart = value;
        rangeEnd = null;

        updateRangeInformation();
        renderCalendar();

        return;
    }


    // =====================================================
    // FIRST DATE
    // =====================================================

    if (!rangeStart) {

        rangeStart = value;
        rangeEnd = null;

        updateRangeInformation();
        renderCalendar();

        return;
    }


    // =====================================================
    // SAME DATE = SINGLE-DAY BOOKING
    // =====================================================

    if (value === rangeStart) {

        rangeEnd = value;

        updateRangeInformation();
        renderCalendar();

        return;
    }


    // =====================================================
    // EARLIER DATE BECOMES NEW START
    // =====================================================

    if (value < rangeStart) {

        rangeStart = value;
        rangeEnd = null;

        updateRangeInformation();
        renderCalendar();

        return;
    }


    // =====================================================
    // CHECK COMPLETE RANGE
    // =====================================================

    if (!isRangeAvailable(rangeStart, value)) {

        calendarDateInfo.textContent =
            "This range contains a booked or unavailable date. Please choose another end date.";

        return;
    }


    // =====================================================
    // SET END DATE
    // =====================================================

    rangeEnd = value;

    updateRangeInformation();
    renderCalendar();
}

  // =====================================================
  // RANGE INFORMATION
  // =====================================================

  function updateRangeInformation() {
    if (!selectedRangeBox) {
      return;
    }

    if (!rangeStart) {
      selectedRangeBox.style.display = "none";

      calendarDateInfo.textContent = "Select your event start date.";

      if (continueBookingButton) {
        continueBookingButton.disabled = true;
      }

      return;
    }

    selectedRangeBox.style.display = "block";

    selectedStartDate.textContent = displayDate(rangeStart);

    if (!rangeEnd) {
      selectedEndDate.textContent = "Select end date";

      selectedRangeDays.textContent = "Select your event end date.";

      selectedRangeStatus.innerHTML = `
                <iconify-icon
                    icon="mdi:information-outline"
                ></iconify-icon>

                Choose an end date.
            `;

      calendarDateInfo.textContent =
        "Start date selected. Now choose your end date.";

      if (continueBookingButton) {
        continueBookingButton.disabled = true;
      }

      return;
    }

    const days = numberOfDays(rangeStart, rangeEnd);

    selectedEndDate.textContent = displayDate(rangeEnd);

    selectedRangeDays.textContent =
      days === 1 ? "1 day selected" : `${days} days selected`;

    selectedRangeStatus.innerHTML = `
            <iconify-icon
                icon="mdi:check-circle-outline"
            ></iconify-icon>

            ${
              days === 1
                ? "Single-day booking is available."
                : "All selected dates are available."
            }
        `;

    calendarDateInfo.textContent = "Selected booking dates are available.";

    if (continueBookingButton) {
      continueBookingButton.disabled = false;
    }
  }

  // =====================================================
  // MONTH NAVIGATION
  // =====================================================

  calendarPrev.addEventListener("click", function () {
    currentDate.setMonth(currentDate.getMonth() - 1);

    renderCalendar();
  });

  calendarNext.addEventListener("click", function () {
    currentDate.setMonth(currentDate.getMonth() + 1);

    renderCalendar();
  });

  // =====================================================
  // CONTINUE BOOKING
  // =====================================================

  if (continueBookingButton) {
    continueBookingButton.addEventListener("click", function (event) {
      event.preventDefault();

      /*
       * User must select both
       * start and end date.
       */

      if (!rangeStart || !rangeEnd) {
        return;
      }

      /*
       * Existing booking page URL.
       */

      const bookingUrl = new URL(
        continueBookingButton.href,
        window.location.origin,
      );

      /*
       * Send selected start date.
       *
       * Example:
       * 2026-10-05
       */

      bookingUrl.searchParams.set("start_date", rangeStart);

      /*
       * Send selected end date.
       *
       * Example:
       * 2026-10-07
       */

      bookingUrl.searchParams.set("end_date", rangeEnd);

      /*
       * Open booking page.
       */

      window.location.href = bookingUrl.toString();
    });
  }
});
