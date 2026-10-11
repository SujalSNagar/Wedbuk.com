document.addEventListener("DOMContentLoaded", function () {

    if (window.__vendorFiltersReady) return;
    window.__vendorFiltersReady = true;

    const filterContainer = document.getElementById("vendorFilters");
    const applyButton     = document.getElementById("applyVendorFilters");

    if (!filterContainer || !applyButton) {
        return;
    }

    const openButton  = document.getElementById("openVendorFilters");
    const closeButton = document.getElementById("closeVendorFilters");
    const overlay     = document.getElementById("vendorFiltersOverlay");
    const clearButton = document.getElementById("clearVendorFilters");
    const countBadge  = document.getElementById("vendorFiltersCount");

    const DEFAULT_MIN = "0";
    const DEFAULT_MAX = "20000000";


    /* =====================================================
       BOTTOM SHEET OPEN / CLOSE
       ===================================================== */

    function openSheet() {
        filterContainer.classList.add("open");
        if (overlay) overlay.classList.add("show");
        document.body.style.overflow = "hidden";
    }

    function closeSheet() {
        filterContainer.classList.remove("open");
        if (overlay) overlay.classList.remove("show");
        document.body.style.overflow = "";
    }

    if (openButton)  openButton.addEventListener("click", openSheet);
    if (closeButton) closeButton.addEventListener("click", closeSheet);
    if (overlay)     overlay.addEventListener("click", closeSheet);

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") closeSheet();
    });


    /* =====================================================
       ACTIVE FILTER COUNT (button pe badge)
       ===================================================== */

    function updateCount() {

        if (!countBadge) return;

        const params = new URLSearchParams(window.location.search);
        const keys = new Set();

        params.forEach(function (value, key) {

            if (key === "q" || key === "page" || key === "sort" || key === "ordering") return;
            if (key === "min_price" && value === DEFAULT_MIN) return;
            if (key === "max_price" && value === DEFAULT_MAX) return;
            if (!value) return;

            keys.add(key);
        });

        if (keys.size > 0) {
            countBadge.textContent = keys.size;
            countBadge.hidden = false;
        } else {
            countBadge.hidden = true;
        }
    }

    updateCount();


    /* =====================================================
       URL HELPERS
       ===================================================== */

    function removeFilterParams(params) {

        ["city", "guests", "min_price", "max_price",
         "pricing_type", "category", "service"].forEach(function (key) {
            params.delete(key);
        });

        Array.from(params.keys()).forEach(function (key) {
            if (key.startsWith("attribute_")) {
                params.delete(key);
            }
        });
    }

    function goTo(params) {

        const searchUrl = window.vendorFilterUrl || "/listings/search/";
        const query = params.toString();

        window.location.href =
            searchUrl + (query ? "?" + query : "");
    }


    /* =====================================================
       CLEAR ALL
       ===================================================== */

    if (clearButton) {
        clearButton.addEventListener("click", function () {

            const params = new URLSearchParams(window.location.search);

            removeFilterParams(params);
            params.delete("page");

            goTo(params);
        });
    }


    /* =====================================================
       APPLY
       ===================================================== */

    applyButton.addEventListener("click", function () {

        const params = new URLSearchParams(window.location.search);

        removeFilterParams(params);
        params.delete("page");


        // CITY
        const city = filterContainer.querySelector("#filterCity");
        if (city && city.value) {
            params.set("city", city.value);
        }

        // GUESTS
        const guests = filterContainer.querySelector('input[name="guests"]:checked');
        if (guests && guests.value) {
            params.set("guests", guests.value);
        }

        // PRICING TYPE
        const pricing = filterContainer.querySelector('input[name="pricing_type"]:checked');
        if (pricing && pricing.value) {
            params.set("pricing_type", pricing.value);
        }

        // MIN PRICE (sirf tab jab default se alag ho)
        const minPrice = filterContainer.querySelector("#filterMinPrice");
        if (minPrice && minPrice.value !== "" && minPrice.value !== DEFAULT_MIN) {
            params.set("min_price", minPrice.value);
        }

        // MAX PRICE (sirf tab jab default se alag ho)
        const maxPrice = filterContainer.querySelector("#filterMaxPrice");
        if (maxPrice && maxPrice.value !== "" && maxPrice.value !== DEFAULT_MAX) {
            params.set("max_price", maxPrice.value);
        }

        // CATEGORY (multiple)
        filterContainer
            .querySelectorAll('input[name="category"]:checked')
            .forEach(function (cb) {
                params.append("category", cb.value);
            });

        // SERVICE (multiple)
        filterContainer
            .querySelectorAll('input[name="service"]:checked')
            .forEach(function (cb) {
                params.append("service", cb.value);
            });

        // DYNAMIC ATTRIBUTES
        filterContainer
            .querySelectorAll('input[type="checkbox"][name^="attribute_"]:checked')
            .forEach(function (cb) {
                params.append(cb.name, cb.value);
            });

        closeSheet();
        goTo(params);
    });


        /* =====================================================
       CUSTOM CITY DROPDOWN (searchable)
       ===================================================== */

    (function () {

        const select = filterContainer.querySelector("#filterCity");
        if (!select) return;

        const wrap = select.closest(".filter-select-wrap");
        if (!wrap) return;

        if (wrap.querySelector(".filter-dd-btn")) return;

        select.classList.add("is-enhanced");

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "filter-dd-btn";

        const panel = document.createElement("div");
        panel.className = "filter-dd-panel";

        const search = document.createElement("input");
        search.type = "text";
        search.className = "filter-dd-search";
        search.placeholder = "Search city...";

        const list = document.createElement("ul");
        list.className = "filter-dd-list";

        panel.appendChild(search);
        panel.appendChild(list);
        wrap.appendChild(btn);
        wrap.appendChild(panel);

        function closePanel() {
            panel.classList.remove("show");
        }

        function renderButton() {
            const current = select.options[select.selectedIndex];
            btn.textContent = current ? current.textContent.trim() : "All Cities";
        }

        function renderList(filter) {

            list.innerHTML = "";
            const term = (filter || "").toLowerCase();
            let found = 0;

            Array.from(select.options).forEach(function (opt) {

                const text = opt.textContent.trim();
                if (term && text.toLowerCase().indexOf(term) === -1) return;

                const li = document.createElement("li");
                li.textContent = text;

                if (opt.value === select.value) {
                    li.classList.add("selected");
                }

                li.addEventListener("click", function () {
                    select.value = opt.value;
                    select.dispatchEvent(new Event("change", { bubbles: true }));
                    renderButton();
                    closePanel();
                });

                list.appendChild(li);
                found++;
            });

            if (!found) {
                const empty = document.createElement("li");
                empty.className = "empty";
                empty.textContent = "No city found";
                list.appendChild(empty);
            }
        }

        btn.addEventListener("click", function (e) {
            e.stopPropagation();
            const willOpen = !panel.classList.contains("show");
            panel.classList.toggle("show", willOpen);
            if (willOpen) {
                search.value = "";
                renderList("");
                setTimeout(function () { search.focus(); }, 50);
                const selected = list.querySelector(".selected");
                if (selected) selected.scrollIntoView({ block: "center" });
            }
        });

        search.addEventListener("input", function () {
            renderList(search.value);
        });

        panel.addEventListener("click", function (e) {
            e.stopPropagation();
        });

        document.addEventListener("click", closePanel);

        renderButton();
        renderList("");

    })();

});