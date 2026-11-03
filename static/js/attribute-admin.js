document.addEventListener("DOMContentLoaded", function () {
    const categorySelect = document.getElementById("id_category");
    const allCheckbox = document.getElementById("id_applies_to_all_services");
    const servicesBox = document.getElementById("id_services");

    if (!categorySelect || !allCheckbox || !servicesBox) return;

    const inputs = Array.from(
        servicesBox.querySelectorAll('input[type="checkbox"]')
    );
    if (!inputs.length) return;

    // ---------- 1. Group services by category ----------
    const groups = new Map();

    inputs.forEach(function (input) {
        const catId = input.dataset.categoryId;
        const item = input.closest("label").parentElement;

        if (!groups.has(catId)) {
            groups.set(catId, {
                id: catId,
                name: input.dataset.categoryName || "Category " + catId,
                items: [],
                inputs: [],
            });
        }
        const g = groups.get(catId);
        g.items.push(item);
        g.inputs.push(input);
    });

    groups.forEach(function (g) {
        const details = document.createElement("details");
        details.style.margin = "0 0 8px";
        details.style.padding = "6px 10px";
        details.style.border = "1px solid #ddd";
        details.style.borderRadius = "6px";

        const summary = document.createElement("summary");
        summary.style.cursor = "pointer";
        summary.style.fontWeight = "600";

        const toggle = document.createElement("input");
        toggle.type = "checkbox";
        toggle.style.margin = "0 8px 0 0";
        toggle.title = "Select all in " + g.name;

        const title = document.createElement("span");
        title.textContent = g.name;

        summary.appendChild(toggle);
        summary.appendChild(title);
        details.appendChild(summary);

        const body = document.createElement("div");
        body.style.padding = "6px 0 0 4px";
        g.items.forEach(function (item) {
            body.appendChild(item);
        });
        details.appendChild(body);

        g.details = details;
        g.toggle = toggle;
        g.title = title;

        toggle.addEventListener("click", function (e) {
            e.stopPropagation(); // don't collapse/expand the group
        });
        toggle.addEventListener("change", function () {
            g.inputs.forEach(function (i) {
                i.checked = toggle.checked;
            });
            refreshGroup(g);
        });

        g.inputs.forEach(function (i) {
            i.addEventListener("change", function () {
                refreshGroup(g);
            });
        });

        servicesBox.appendChild(details);
    });

    function refreshGroup(g) {
        const checked = g.inputs.filter(function (i) {
            return i.checked;
        }).length;
        g.toggle.checked = checked === g.inputs.length;
        g.toggle.indeterminate = checked > 0 && checked < g.inputs.length;
        g.title.textContent =
            g.name + (checked ? " (" + checked + "/" + g.inputs.length + ")" : "");
    }

    // ---------- 2. Selected category: top par + open ----------
    function focusSelectedCategory() {
        const selectedId = categorySelect.value;

        groups.forEach(function (g) {
            const hasChecked = g.inputs.some(function (i) {
                return i.checked;
            });
            g.details.open = g.id === selectedId || hasChecked;
        });

        const selectedGroup = groups.get(selectedId);
        if (selectedGroup) {
            servicesBox.prepend(selectedGroup.details);
        }
    }

    // ---------- 3. Apply to all services ----------
    function setAllMode(on) {
        inputs.forEach(function (i) {
            if (on) {
                if (i.dataset.prev === undefined) {
                    i.dataset.prev = i.checked ? "1" : "0";
                }
                i.checked = true;
                i.disabled = true;
            } else {
                if (i.dataset.prev !== undefined) {
                    i.checked = i.dataset.prev === "1";
                    delete i.dataset.prev;
                }
                i.disabled = false;
            }
        });

        groups.forEach(function (g) {
            g.toggle.disabled = on;
            if (on) g.details.open = true;
            refreshGroup(g);
        });

        if (!on) focusSelectedCategory();
    }

    allCheckbox.addEventListener("change", function () {
        setAllMode(allCheckbox.checked);
    });
    categorySelect.addEventListener("change", function () {
        if (!allCheckbox.checked) focusSelectedCategory();
    });

    // ---------- init ----------
    groups.forEach(refreshGroup);
    focusSelectedCategory();
    if (allCheckbox.checked) setAllMode(true);
});