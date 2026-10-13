document.addEventListener("DOMContentLoaded", function () {


    /* =====================================================
       PLANNER
       ===================================================== */

    const planner =
        document.querySelector(".budget-planner-section");


    if (!planner) {
        return;
    }


    /* =====================================================
       ELEMENTS
       ===================================================== */

    const stateSelect =
        document.getElementById("plannerState");

    const citySelect =
        document.getElementById("plannerCity");

    const locationHint =
        document.getElementById("plannerLocationHint");

    const dateInput =
        document.getElementById("plannerDate");

    const endDateInput =
        document.getElementById("plannerEndDate");

    const guestRange =
        document.getElementById("plannerGuests");

    const guestValue =
        document.getElementById("plannerGuestsValue");

    const guestSummary =
        document.getElementById("plannerGuestSummary");

    const budgetInput =
        document.getElementById("weddingBudget");

    const budgetRange =
        document.getElementById("weddingBudgetRange");

    const budgetDisplay =
        document.getElementById("plannerBudgetDisplay");

    const plannerTotal =
        document.getElementById("plannerTotal");

    const locationSummary =
        document.getElementById("plannerLocationSummary");

    const dateSummary =
        document.getElementById("plannerDateSummary");

    const selectedServices =
        document.getElementById("plannerSelectedServices");

    const plannerError =
        document.getElementById("plannerError");

    const findButton =
        document.getElementById("plannerFindOptions");

    const resetButton =
        document.getElementById("plannerReset");

    const selectAllButton =
        document.getElementById("plannerSelectAll");


    /* =====================================================
       DATA
       ===================================================== */

    const MIN_BUDGET = 10000;

    const MAX_BUDGET = 10000000;


    /* =====================================================
       CURRENCY
       ===================================================== */

    function formatCurrency(value) {

        return (
            "₹" +
            Number(value).toLocaleString("en-IN")
        );

    }


    /* =====================================================
       BUDGET SLIDER
       ===================================================== */

    function budgetToSlider(budget) {

        const minLog =
            Math.log(MIN_BUDGET);

        const maxLog =
            Math.log(MAX_BUDGET);

        const valueLog =
            Math.log(budget);

        const position =
            (
                (valueLog - minLog) /
                (maxLog - minLog)
            ) * 1000;

        return Math.round(position);

    }


    function sliderToBudget(position) {

        const minLog =
            Math.log(MIN_BUDGET);

        const maxLog =
            Math.log(MAX_BUDGET);

        const ratio =
            Number(position) / 1000;

        const value =
            Math.exp(
                minLog +
                ratio *
                (maxLog - minLog)
            );

        return (
            Math.round(value / 1000) * 1000
        );

    }


    function updateBudgetSliderProgress(position) {

        const percentage =
            (Number(position) / 1000) * 100;

        budgetRange.style.setProperty(
            "--range-progress",
            percentage + "%"
        );

    }


    /* =====================================================
       STATE -> CITY
       ===================================================== */

    async function loadCitiesForState(stateId) {


        citySelect.innerHTML = `
            <option value="">
                Select City
            </option>
        `;

        citySelect.disabled = true;


        if (!stateId) {

            locationHint.textContent =
                "Select a state first";

            updateLocationSummary();

            return;

        }


        locationHint.textContent =
            "Loading cities...";


        try {

            const response =
                await fetch(
                    `${window.citiesByStateUrl}?state_id=${encodeURIComponent(stateId)}`
                );


            if (!response.ok) {

                throw new Error(
                    "Could not load cities."
                );

            }


            const data =
                await response.json();


            const cities =
                data.cities || [];


            if (!cities.length) {

                citySelect.innerHTML = `
                    <option value="">
                        No cities available
                    </option>
                `;

                locationHint.textContent =
                    "No cities available for this state.";

                updateLocationSummary();

                return;

            }


            cities.forEach(function (city) {

                const option =
                    document.createElement("option");

                option.value =
                    city.id;

                option.textContent =
                    city.name;

                citySelect.appendChild(
                    option
                );

            });


            citySelect.disabled = false;

            locationHint.textContent =
                "Select your city";


        } catch (error) {

            console.error(
                "Budget Planner city loading error:",
                error
            );


            citySelect.innerHTML = `
                <option value="">
                    Unable to load cities
                </option>
            `;

            locationHint.textContent =
                "Unable to load cities.";

        }


        updateLocationSummary();

    }


    /* =====================================================
       LOCATION SUMMARY
       ===================================================== */

    function updateLocationSummary() {

        if (!stateSelect || !citySelect) {
            return;
        }


        const stateOption =
            stateSelect.options[
                stateSelect.selectedIndex
            ];


        const cityOption =
            citySelect.options[
                citySelect.selectedIndex
            ];


        const stateName =
            stateOption &&
            stateOption.value
                ? stateOption.textContent.trim()
                : "";


        const cityName =
            cityOption &&
            cityOption.value
                ? cityOption.textContent.trim()
                : "";


        if (cityName && stateName) {

            locationSummary.textContent =
                `${cityName}, ${stateName}`;

        } else if (stateName) {

            locationSummary.textContent =
                stateName;

        } else {

            locationSummary.textContent =
                "Select city";

        }

    }


    /* =====================================================
       DATE
       ===================================================== */

    function formatDate(value) {

        const date =
            new Date(
                value + "T00:00:00"
            );

        return date.toLocaleDateString(
            "en-IN",
            {
                day: "2-digit",
                month: "short",
                year: "numeric"
            }
        );

    }


    function updateDateSummary() {

        const startDate =
            dateInput.value;

        const endDate =
            endDateInput.value;


        if (!startDate && !endDate) {

            dateSummary.textContent =
                "Not selected";

            return;

        }


        if (startDate && endDate) {

            dateSummary.textContent =
                `${formatDate(startDate)} – ${formatDate(endDate)}`;

            return;

        }


        if (startDate) {

            dateSummary.textContent =
                formatDate(startDate);

            return;

        }


        dateSummary.textContent =
            formatDate(endDate);

    }


    /* =====================================================
       GUESTS
       ===================================================== */

    function updateGuests() {

        const guests =
            Number(guestRange.value);


        guestValue.textContent =
            `${guests.toLocaleString("en-IN")} Guests`;


        guestSummary.textContent =
            guests.toLocaleString("en-IN");


        const percentage =
            (
                (guests - 20) /
                (2000 - 20)
            ) * 100;


        guestRange.style.setProperty(
            "--range-progress",
            percentage + "%"
        );

    }


    /* =====================================================
       BUDGET
       ===================================================== */

    function updateBudgetFromInput() {

        let budget =
            Number(budgetInput.value);


        if (!budget || budget < MIN_BUDGET) {
            budget = MIN_BUDGET;
        }


        if (budget > MAX_BUDGET) {
            budget = MAX_BUDGET;
        }


        budgetInput.value =
            budget;


        const sliderPosition =
            budgetToSlider(budget);


        budgetRange.value =
            sliderPosition;


        updateBudgetSliderProgress(
            sliderPosition
        );


        budgetDisplay.textContent =
            formatCurrency(budget);


        plannerTotal.textContent =
            formatCurrency(budget);

    }


    function updateBudgetFromSlider() {

        const budget =
            sliderToBudget(
                budgetRange.value
            );


        budgetInput.value =
            budget;


        budgetDisplay.textContent =
            formatCurrency(budget);


        plannerTotal.textContent =
            formatCurrency(budget);


        updateBudgetSliderProgress(
            budgetRange.value
        );

    }


    /* =====================================================
       CATEGORIES
       ===================================================== */

    function getSelectedCategories() {

        return Array.from(
            planner.querySelectorAll(
                'input[name="planner_category"]:checked'
            )
        ).map(
            function (input) {

                return {

                    slug:
                        input.value,

                    name:
                        input
                            .closest(
                                ".planner-service-option"
                            )
                            .querySelector("span")
                            .textContent
                            .trim()

                };

            }
        );

    }


    function updateSelectedCategories() {

        const categories =
            getSelectedCategories();


        selectedServices.innerHTML =
            "";


        if (!categories.length) {

            selectedServices.innerHTML = `
                <span class="planner-no-selection">
                    Select what you need
                </span>
            `;

            return;

        }


        categories.forEach(
            function (category) {

                const tag =
                    document.createElement("span");


                tag.textContent =
                    category.name;


                selectedServices.appendChild(
                    tag
                );

            }
        );

    }


    function toggleAllCategories() {

        const checkboxes =
            planner.querySelectorAll(
                'input[name="planner_category"]'
            );


        const allSelected =
            checkboxes.length > 0 &&
            Array.from(checkboxes)
                .every(
                    function (checkbox) {
                        return checkbox.checked;
                    }
                );


        checkboxes.forEach(
            function (checkbox) {

                checkbox.checked =
                    !allSelected;

            }
        );


        updateSelectedCategories();

    }
function showPlannerError(message, target) {
    clearPlannerError();

    plannerError.innerHTML = `
        <span class="planner-error-icon">!</span>
        <span>${message}</span>
    `;

    plannerError.classList.add("is-visible");
    plannerError.setAttribute("role", "alert");

    if (target) {
        target.classList.add("planner-invalid");

        target.scrollIntoView({
            behavior: "smooth",
            block: "center"
        });

        target.focus({ preventScroll: true });
    }
}

function clearPlannerError(target) {
    if (target) {
        target.classList.remove("planner-invalid");
        return;
    }

    plannerError.textContent = "";
    plannerError.classList.remove("is-visible");
    plannerError.removeAttribute("role");

    planner.querySelectorAll(".planner-invalid")
        .forEach(function (field) {
            field.classList.remove("planner-invalid");
        });
}

    /* =====================================================
       FIND OPTIONS
       ===================================================== */

    function findMatchingOptions() {

        clearPlannerError();


        /* ---------------------------------------------
           STATE VALIDATION
           --------------------------------------------- */

        const stateId =
            stateSelect.value;


if (!stateId) {
    showPlannerError(
        "Please select your event state.",
        stateSelect
    );
    return;
}


        /* ---------------------------------------------
           CITY VALIDATION
           --------------------------------------------- */

        const cityId =
            citySelect.value;


if (!cityId) {
    showPlannerError(
        "Please select your event city.",
        citySelect
    );
    return;
}


        /* ---------------------------------------------
           DATE VALIDATION
           --------------------------------------------- */

        const startDate =
            dateInput.value;

        const endDate =
            endDateInput.value;


if (endDate && !startDate) {
    showPlannerError(
        "Please select a start date first.",
        dateInput
    );
    return;
}


if (startDate && endDate && endDate < startDate) {
    showPlannerError(
        "End date cannot be before start date.",
        endDateInput
    );
    return;
}


        /* ---------------------------------------------
           GUESTS
           --------------------------------------------- */

        const guests =
            Number(
                guestRange.value
            );


        /* ---------------------------------------------
           BUDGET
           --------------------------------------------- */

        const budget =
            Number(
                budgetInput.value
            );


        /* ---------------------------------------------
           CATEGORIES
           --------------------------------------------- */

        const categories =
            getSelectedCategories();


if (!categories.length) {
    showPlannerError(
        "Please select at least one service category.",
        planner.querySelector(".planner-service-options")
    );
    return;
}


        /* ---------------------------------------------
           QUERY PARAMETERS
           --------------------------------------------- */

        const params =
            new URLSearchParams();


        params.set(
            "state",
            stateId
        );


        params.set(
            "city",
            cityId
        );


        params.set(
            "guests",
            guests
        );


        params.set(
            "budget",
            budget
        );


        if (startDate) {

            params.set(
                "date",
                startDate
            );

        }


        if (endDate) {

            params.set(
                "end_date",
                endDate
            );

        }


        categories.forEach(
            function (category) {

                params.append(
                    "category",
                    category.slug
                );

            }
        );


        /* ---------------------------------------------
           GO TO BUDGET RESULTS
           --------------------------------------------- */

        window.location.href =
            `/listings/budget-results/?${params.toString()}`;

    }


    /* =====================================================
       RESET
       ===================================================== */

    function resetPlanner() {


        /* ---------------------------------------------
           LOCATION
           --------------------------------------------- */

        stateSelect.value =
            "";


        citySelect.innerHTML = `
            <option value="">
                Select City
            </option>
        `;


        citySelect.disabled =
            true;


        locationHint.textContent =
            "Select a state first";


        /* ---------------------------------------------
           DATE
           --------------------------------------------- */

        dateInput.value =
            "";

        endDateInput.value =
            "";

        endDateInput.min =
            today;


        /* ---------------------------------------------
           GUESTS
           --------------------------------------------- */

        guestRange.value =
            200;


        /* ---------------------------------------------
           BUDGET
           --------------------------------------------- */

        budgetInput.value =
            200000;


        /* ---------------------------------------------
           ERROR
           --------------------------------------------- */

        plannerError.textContent =
            "";


        /* ---------------------------------------------
           CATEGORIES
           --------------------------------------------- */

        planner
            .querySelectorAll(
                'input[name="planner_category"]'
            )
            .forEach(
                function (checkbox) {

                    checkbox.checked =
                        false;

                }
            );


        /* ---------------------------------------------
           UPDATE EVERYTHING
           --------------------------------------------- */

        updateGuests();

        updateBudgetFromInput();

        updateDateSummary();

        updateLocationSummary();

        updateSelectedCategories();

    }


    /* =====================================================
       EVENT LISTENERS
       ===================================================== */


    /* ---------------------------------------------
       STATE CHANGE
       --------------------------------------------- */

    if (stateSelect) {

        stateSelect.addEventListener(
            "change",
            function () {

                loadCitiesForState(
                    this.value
                );

            }
        );

    }


    /* ---------------------------------------------
       CITY CHANGE
       --------------------------------------------- */

    if (citySelect) {

        citySelect.addEventListener(
            "change",
            function () {

                updateLocationSummary();

            }
        );

    }


    /* ---------------------------------------------
       START DATE
       --------------------------------------------- */

    dateInput.addEventListener(
        "change",
        function () {

            if (dateInput.value) {

                endDateInput.min =
                    dateInput.value;


                if (
                    endDateInput.value &&
                    endDateInput.value < dateInput.value
                ) {

                    endDateInput.value =
                        "";

                }

            } else {

                endDateInput.min =
                    today;

                endDateInput.value =
                    "";

            }


            updateDateSummary();

        }
    );


    /* ---------------------------------------------
       END DATE
       --------------------------------------------- */

    endDateInput.addEventListener(
        "change",
        function () {

            updateDateSummary();

        }
    );


    /* ---------------------------------------------
       GUESTS
       --------------------------------------------- */

    guestRange.addEventListener(
        "input",
        updateGuests
    );


    /* ---------------------------------------------
       BUDGET SLIDER
       --------------------------------------------- */

    budgetRange.addEventListener(
        "input",
        updateBudgetFromSlider
    );


    /* ---------------------------------------------
       BUDGET INPUT
       --------------------------------------------- */

    budgetInput.addEventListener(
        "input",
        updateBudgetFromInput
    );


    /* ---------------------------------------------
       FIND OPTIONS
       --------------------------------------------- */

    findButton.addEventListener(
        "click",
        findMatchingOptions
    );


    /* ---------------------------------------------
       RESET
       --------------------------------------------- */

    resetButton.addEventListener(
        "click",
        resetPlanner
    );


    /* ---------------------------------------------
       SELECT ALL
       --------------------------------------------- */

    selectAllButton.addEventListener(
        "click",
        toggleAllCategories
    );


    /* ---------------------------------------------
       CATEGORY CHECKBOXES
       --------------------------------------------- */

    planner
        .querySelectorAll(
            'input[name="planner_category"]'
        )
        .forEach(
            function (checkbox) {

                checkbox.addEventListener(
                    "change",
                    updateSelectedCategories
                );

            }
        );


    /* =====================================================
       DATE MINIMUM
       ===================================================== */

    const today =
        new Date()
            .toISOString()
            .split("T")[0];


    dateInput.min =
        today;


    endDateInput.min =
        today;


        [stateSelect, citySelect, dateInput, endDateInput]
    .forEach(function (field) {
        field.addEventListener("change", function () {
            clearPlannerError(field);
            plannerError.textContent = "";
            plannerError.classList.remove("is-visible");
        });
    });

planner.querySelectorAll(
    'input[name="planner_category"]'
).forEach(function (checkbox) {
    checkbox.addEventListener("change", function () {
        const categories = getSelectedCategories();

        if (categories.length) {
            clearPlannerError(
                planner.querySelector(".planner-service-options")
            );
            plannerError.textContent = "";
            plannerError.classList.remove("is-visible");
        }
    });
});

    /* =====================================================
       INITIALIZE
       ===================================================== */

    citySelect.disabled =
        true;


    locationHint.textContent =
        "Select a state first";


    updateGuests();

    updateBudgetFromInput();

    updateDateSummary();

    updateLocationSummary();

    updateSelectedCategories();


});