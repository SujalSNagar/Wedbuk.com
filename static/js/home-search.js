
document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("search-input");
    const cityOptions = document.querySelectorAll(
        "#wedbook-search-cities option"
    );

    if (!searchInput) return;

    function getMatchingCity() {
        const value = searchInput.value.trim().toLowerCase();

        return Array.from(cityOptions).find(function (option) {
            return option.value.trim().toLowerCase() === value;
        });
    }

    function getCsrfToken() {
        const cookie = document.cookie
            .split("; ")
            .find(function (item) {
                return item.startsWith("csrftoken=");
            });

        return cookie ? decodeURIComponent(cookie.split("=")[1]) : "";
    }

    async function saveSelectedCity(cityId) {
        const response = await fetch(window.selectCityUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "X-CSRFToken": getCsrfToken()
            },
            body: new URLSearchParams({
                city_id: cityId
            }),
            credentials: "same-origin"
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.message || "Could not select city.");
        }

        // Update the header immediately.
        const headerCity = document.getElementById("selected-city-label");

        if (headerCity) {
            headerCity.textContent = data.city;
        }
    }


});



document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("search-input");

    if (!searchInput) return;
});
