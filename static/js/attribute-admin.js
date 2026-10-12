/* Admin: CategoryAttribute form
   Service dropdown shows only the services of the selected category.
   Service labels look like "Venue - Banquet Hall" (Service.__str__),
   so the category name is used as the prefix to filter. */

document.addEventListener("DOMContentLoaded", function () {
  var category = document.getElementById("id_category");
  var service = document.getElementById("id_service");

  if (!category || !service) {
    return;
  }

  var allOptions = Array.prototype.slice
    .call(service.options)
    .map(function (option) {
      return { value: option.value, text: option.text };
    });

  function rebuild() {
    var selected = category.options[category.selectedIndex];
    var categoryName = selected && selected.value ? selected.text.trim() : "";
    var prefix = categoryName + " - ";
    var current = service.value;

    service.innerHTML = "";

    allOptions.forEach(function (item) {
      var option;

      if (!item.value) {
        option = new Option(item.text, "");
        service.appendChild(option);
        return;
      }

      if (categoryName && item.text.indexOf(prefix) === 0) {
        option = new Option(item.text.slice(prefix.length), item.value);
        service.appendChild(option);
      }
    });

    service.value = current;

    if (service.value !== current) {
      service.value = "";
    }
  }

  category.addEventListener("change", rebuild);
  rebuild();
});