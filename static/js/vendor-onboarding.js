document.addEventListener("DOMContentLoaded", function () {
  const stateSelect = document.getElementById("id_state");
  const citySelect = document.getElementById("id_city");
  const form = document.getElementById("vendorOnboardingForm");

  if (!stateSelect || !citySelect || !form) {
    console.error("State, City or onboarding form not found.");
    return;
  }

  const citiesUrl = form.dataset.citiesUrl;

  stateSelect.addEventListener("change", function () {
    const stateId = this.value;

    citySelect.innerHTML = "";

    const defaultOption = document.createElement("option");

    defaultOption.value = "";
    defaultOption.textContent = "Select City";

    citySelect.appendChild(defaultOption);

    if (!stateId) {
      citySelect.disabled = true;
      return;
    }

    citySelect.disabled = true;

    fetch(`${citiesUrl}?state_id=${stateId}`)
      .then(function (response) {
        if (!response.ok) {
          throw new Error(`HTTP error: ${response.status}`);
        }

        return response.json();
      })
      .then(function (data) {
        data.cities.forEach(function (city) {
          const option = document.createElement("option");

          option.value = city.id;
          option.textContent = city.name;

          citySelect.appendChild(option);
        });

        citySelect.disabled = false;
      })
      .catch(function (error) {
        console.error("Error loading cities:", error);

        citySelect.innerHTML = "";

        const errorOption = document.createElement("option");

        errorOption.value = "";
        errorOption.textContent = "Unable to load cities";

        citySelect.appendChild(errorOption);

        citySelect.disabled = false;
      });
  });
});
