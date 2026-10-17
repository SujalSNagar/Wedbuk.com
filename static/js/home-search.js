
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

    // Selecting a city suggestion or leaving an exact city name
    // saves it to the Django session.
    searchInput.addEventListener("change", async function () {
        const option = getMatchingCity();

        if (!option) return;

        const cityId = option.dataset.cityId;

        if (!cityId) return;

        try {
            await saveSelectedCity(cityId);
        } catch (error) {
            console.error("City selection failed:", error);
        }
    });
});



window.addEventListener("pageshow", function () {
    fetch(window.location.href, {
        method: "GET",
        credentials: "same-origin",
        cache: "no-store",
        headers: {
            "X-Requested-With": "XMLHttpRequest"
        }
    })
    .then(function (response) {
        if (!response.ok) return null;
        return response.text();
    })
    .then(function (html) {
        if (!html) return;

        const doc = new DOMParser().parseFromString(html, "text/html");

        const freshCity = doc.getElementById("selected-city-label");
        const currentCity = document.getElementById("selected-city-label");

        if (freshCity && currentCity) {
            currentCity.textContent = freshCity.textContent.trim();
        }
    })
    .catch(function (error) {
        console.error("Could not refresh selected city:", error);
    });
});
