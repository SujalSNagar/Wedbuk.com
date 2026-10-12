document.addEventListener("DOMContentLoaded", function () {
  const listingForm = document.getElementById("listingForm");

  if (!listingForm) {
    return;
  }

  /* =========================================================
       COMMON ELEMENTS
       ========================================================= */

  const page = document.getElementById("listingFormPage");

  const citiesUrl =
    listingForm.dataset.citiesUrl || (page ? page.dataset.citiesUrl : "");

  const attributesUrl =
    listingForm.dataset.categoryAttributesUrl ||
    (page ? page.dataset.categoryAttributesUrl : "");

  /* =========================================================
       STATE -> CITY
       ========================================================= */

  const stateSelect = document.getElementById("id_listing_state");

  const citySelect = document.getElementById("id_listing_city");

  if (stateSelect && citySelect && citiesUrl) {
    stateSelect.addEventListener("change", function () {
      const stateId = this.value;

      citySelect.innerHTML = "";

      const defaultOption = document.createElement("option");

      defaultOption.value = "";

      defaultOption.textContent = stateId ? "Loading cities..." : "Select City";

      citySelect.appendChild(defaultOption);

      citySelect.disabled = true;

      if (!stateId) {
        return;
      }

      fetch(`${citiesUrl}?state_id=${encodeURIComponent(stateId)}`)
        .then(function (response) {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }

          return response.json();
        })

        .then(function (data) {
          citySelect.innerHTML = "";

          const selectOption = document.createElement("option");

          selectOption.value = "";

          selectOption.textContent = "Select City";

          citySelect.appendChild(selectOption);

          (data.cities || []).forEach(function (city) {
            const option = document.createElement("option");

            option.value = city.id;

            option.textContent = city.name;

            citySelect.appendChild(option);
          });

          citySelect.disabled = false;
        })

        .catch(function (error) {
          console.error("Unable to load cities:", error);

          citySelect.innerHTML = "";

          const errorOption = document.createElement("option");

          errorOption.value = "";

          errorOption.textContent = "Unable to load cities";

          citySelect.appendChild(errorOption);

          citySelect.disabled = false;
        });
    });
  }

  /* =========================================================
       CATEGORY -> SERVICE (single) -> SERVICE ATTRIBUTES
       ========================================================= */

  const categorySelect = document.getElementById("id_category");

  const serviceSelect = document.getElementById("id_service");

  const titleInput = document.getElementById("id_title");

  const attributesContainer =
    document.getElementById("categoryAttributesGrid") ||
    document.getElementById("categoryAttributes");

  const attributesCard = document.getElementById("categoryAttributesCard");

  let lastAutoTitle = "";

  /* Keep a copy of every service option once, then rebuild the
     <select> for the chosen category (hiding <option> is not
     reliable on all browsers). */

  const allServiceOptions = serviceSelect
    ? Array.from(serviceSelect.options)
        .filter(function (option) {
          return option.value;
        })
        .map(function (option) {
          return {
            value: option.value,
            text: option.text.trim(),
            categoryId: option.getAttribute("data-category-id"),
          };
        })
    : [];

  const initialServiceValue = serviceSelect ? serviceSelect.value : "";

  function rebuildServiceOptions(categoryId, keepValue) {
    if (!serviceSelect) {
      return;
    }

    serviceSelect.innerHTML = "";

    const placeholder = document.createElement("option");

    placeholder.value = "";
    placeholder.textContent = categoryId
      ? "Select service"
      : "Select category first";

    serviceSelect.appendChild(placeholder);

    allServiceOptions
      .filter(function (item) {
        return categoryId && String(item.categoryId) === String(categoryId);
      })
      .forEach(function (item) {
        const option = document.createElement("option");

        option.value = item.value;
        option.textContent = item.text;
        option.setAttribute("data-category-id", item.categoryId);

        if (keepValue && String(keepValue) === String(item.value)) {
          option.selected = true;
        }

        serviceSelect.appendChild(option);
      });
  }

  function clearAttributes() {
    if (attributesContainer) {
      attributesContainer.innerHTML = "";
    }

    if (attributesCard) {
      attributesCard.classList.add("is-hidden");
    }
  }

  function updateCategoryUI(updateTitle = true) {
    if (!categorySelect) {
      return;
    }

    const selectedOption = categorySelect.options[categorySelect.selectedIndex];

    if (!selectedOption || !selectedOption.value) {
      rebuildServiceOptions("", "");
      clearAttributes();

      return;
    }

    const categoryId = selectedOption.value;
    const categoryName = selectedOption.text.trim();

    /* AUTOMATIC TITLE */

    if (titleInput && updateTitle) {
      const currentTitle = titleInput.value.trim();

      if (currentTitle === "" || currentTitle === lastAutoTitle) {
        titleInput.value = categoryName;
        lastAutoTitle = categoryName;
      }
    }

    /* New category -> service must be chosen again */

    rebuildServiceOptions(categoryId, "");
    clearAttributes();
  }

  /* =========================================================
       SERVICE ATTRIBUTES (only for the selected service)
       ========================================================= */

  async function loadServiceAttributes(categoryId, serviceId) {
    if (!attributesContainer || !attributesUrl) {
      return;
    }

    if (!categoryId || !serviceId) {
      clearAttributes();

      return;
    }

    try {
      const params = new URLSearchParams();

      params.append("category_id", categoryId);
      params.append("service_id", serviceId);

      const response = await fetch(`${attributesUrl}?${params.toString()}`, {
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      if (!response.ok) {
        throw new Error("Failed to load service attributes.");
      }

      const data = await response.json();

      /* ignore stale responses if the service changed meanwhile */
      if (serviceSelect && String(serviceSelect.value) !== String(serviceId)) {
        return;
      }

      attributesContainer.innerHTML = "";

      if (!data.attributes || data.attributes.length === 0) {
        clearAttributes();

        return;
      }

      if (attributesCard) {
        attributesCard.classList.remove("is-hidden");
      }

      attributesContainer.style.display = "";

      data.attributes.forEach(function (attribute) {
        const wrapper = document.createElement("div");

        wrapper.className = "listing-field";

        const fieldName = `attribute_${attribute.id}`;

        const requiredAttr = attribute.is_required ? "required" : "";

        let fieldHTML = "";

        if (attribute.field_type === "number") {
          fieldHTML = `
            <input type="number" name="${fieldName}" id="${fieldName}"
                   class="form-control" step="any" min="0" ${requiredAttr}>`;
        } else if (attribute.field_type === "boolean") {
          fieldHTML = `
            <select name="${fieldName}" id="${fieldName}"
                    class="form-control" ${requiredAttr}>
              <option value="">Select</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>`;
        } else if (attribute.field_type === "dropdown") {
          const optionsHTML = (attribute.options || [])
            .map(function (option) {
              return `<option value="${escapeHtml(option)}">${escapeHtml(option)}</option>`;
            })
            .join("");

          fieldHTML = `
            <select name="${fieldName}" id="${fieldName}"
                    class="form-control" ${requiredAttr}>
              <option value="">Select</option>
              ${optionsHTML}
            </select>`;
        } else if (attribute.field_type === "multiselect") {
          /* same markup as the Event Types checkboxes */
          wrapper.style.gridColumn = "1 / -1";

          const cardsHTML = (attribute.options || [])
            .map(function (option, index) {
              return `
                <label class="selection-card">
                  <input type="checkbox" name="${fieldName}"
                         id="${fieldName}_${index}"
                         value="${escapeHtml(option)}">
                  <span class="selection-card-content">
                    <span class="selection-card-title">${escapeHtml(option)}</span>
                  </span>
                  <span class="selection-card-check">
                    <span class="iconify" data-icon="solar:check-circle-bold"></span>
                  </span>
                </label>`;
            })
            .join("");

          fieldHTML = `<div class="selection-grid">${cardsHTML}</div>`;
        } else {
          fieldHTML = `
            <input type="text" name="${fieldName}" id="${fieldName}"
                   class="form-control" ${requiredAttr}>`;
        }

        wrapper.innerHTML = `
          <label for="${fieldName}">
            ${escapeHtml(attribute.label)}
            ${attribute.is_required ? "<span>*</span>" : ""}
            ${
              attribute.unit
                ? `<span class="attribute-unit">(${escapeHtml(attribute.unit)})</span>`
                : ""
            }
          </label>

          ${fieldHTML}

          ${
            attribute.help_text
              ? `<small class="field-help">${escapeHtml(attribute.help_text)}</small>`
              : ""
          }`;

        attributesContainer.appendChild(wrapper);
      });

      if (window.Iconify && typeof window.Iconify.scan === "function") {
        window.Iconify.scan(attributesContainer);
      }
    } catch (error) {
      console.error("Service attributes error:", error);
    }
  }

  /* =========================================================
       HTML ESCAPE
       ========================================================= */

  function escapeHtml(value) {
    const div = document.createElement("div");

    div.textContent = value ?? "";

    return div.innerHTML;
  }

  /* =========================================================
       EVENTS
       ========================================================= */

  if (categorySelect) {
    categorySelect.addEventListener("change", function () {
      updateCategoryUI(true);
    });
  }

  if (serviceSelect) {
    serviceSelect.addEventListener("change", function () {
      loadServiceAttributes(
        categorySelect ? categorySelect.value : "",
        serviceSelect.value,
      );
    });
  }

  /* =========================================================
       INITIAL LOAD
       (attributes are already rendered by Django on first load /
        validation errors, so only the service list is rebuilt)
       ========================================================= */

  if (categorySelect) {
    const initialOption = categorySelect.options[categorySelect.selectedIndex];

    if (initialOption && initialOption.value) {
      lastAutoTitle = initialOption.text.trim();

      rebuildServiceOptions(initialOption.value, initialServiceValue);
    } else {
      rebuildServiceOptions("", "");
    }
  }

/* =========================================================
   COVER IMAGE PREVIEW
   ========================================================= */

const coverInput =
    document.getElementById("id_cover_image");

const coverPreview =
    document.getElementById("coverPreview");

let coverObjectUrl = null;


if (
    coverInput &&
    coverPreview
) {

    coverInput.addEventListener(
        "change",
        function () {

            const coverFileName = document.getElementById("coverFileName");

            if (coverFileName) {
              if (this.files.length > 0) {
                coverFileName.textContent = this.files[0].name;
              } else {
                coverFileName.textContent = "No file chosen";
              }
            }

            coverPreview.innerHTML = "";


            if (coverObjectUrl) {

                URL.revokeObjectURL(
                    coverObjectUrl
                );

                coverObjectUrl = null;

            }


            const file =
                this.files[0];


            if (!file) {

                return;

            }


            if (
                !file.type.startsWith("image/")
            ) {

                alert(
                    "Please select a valid image."
                );

                this.value = "";

                return;

            }


            coverObjectUrl =
                URL.createObjectURL(
                    file
                );


            const item =
                document.createElement(
                    "div"
                );


            item.className =
                "single-preview-item";


            const image =
                document.createElement(
                    "img"
                );


            image.src =
                coverObjectUrl;


            image.alt =
                "Cover image preview";


            const removeButton =
                createRemoveButton(
                    "Remove cover image"
                );


            removeButton.addEventListener(
                "click",
                function () {

                    coverInput.value =
                        "";


                    coverPreview.innerHTML =
                        "";


                    if (coverObjectUrl) {

                        URL.revokeObjectURL(
                            coverObjectUrl
                        );

                        coverObjectUrl =
                            null;

                    }

                }
            );


            item.appendChild(
                image
            );


            item.appendChild(
                removeButton
            );


            coverPreview.appendChild(
                item
            );

        }
    );

}


/* =========================================================
   GALLERY IMAGES
   ========================================================= */

const galleryInput =
    document.getElementById(
        "galleryImages"
    );


const galleryPreview =
    document.getElementById(
        "galleryPreview"
    );


let existingGalleryCount = parseInt(page?.dataset.existingGallery || "0", 10);


let selectedGalleryFiles =
    [];


if (
    galleryInput &&
    galleryPreview
) {

    galleryInput.addEventListener(
        "change",
        function () {

            const files =
                Array.from(
                    this.files
                );


            const remainingSlots =
                Math.max(
                    0,
                    8 -
                    existingGalleryCount -
                    selectedGalleryFiles.length
                );


            if (
                files.length >
                remainingSlots
            ) {

                alert(
                    `You can add only ${remainingSlots} more image(s).`
                );

                updateGalleryInput();

                return;

            }


            const invalidFile =
                files.find(
                    function (file) {

                        return !file.type.startsWith(
                            "image/"
                        );

                    }
                );


            if (invalidFile) {

                alert(
                    "Only image files are allowed."
                );

                updateGalleryInput();

                return;

            }


            selectedGalleryFiles =
                selectedGalleryFiles.concat(
                    files
                );


            renderGalleryPreview();

            updateGalleryInput();
            updateGalleryFileName();

        }
    );

}


function renderGalleryPreview() {

    if (!galleryPreview) {

        return;

    }


    galleryPreview.innerHTML =
        "";


    selectedGalleryFiles.forEach(
        function (file, index) {

            const item =
                document.createElement(
                    "div"
                );


            item.className =
                "gallery-preview-item";


            const image =
                document.createElement(
                    "img"
                );


            const objectUrl =
                URL.createObjectURL(
                    file
                );


            image.src =
                objectUrl;


            image.alt =
                `Gallery image ${index + 1}`;


            image.onload =
                function () {

                    URL.revokeObjectURL(
                        objectUrl
                    );

                };


            const number =
                document.createElement(
                    "div"
                );


            number.className =
                "gallery-preview-number";


            number.textContent =
                existingGalleryCount +
                index +
                1;


            const removeButton =
                createRemoveButton(
                    "Remove gallery image"
                );


            removeButton.addEventListener(
                "click",
                function () {

                    selectedGalleryFiles =
                        selectedGalleryFiles.filter(
                            function (
                                selectedFile
                            ) {

                                return (
                                    selectedFile !==
                                    file
                                );

                            }
                        );


                    renderGalleryPreview();

                    updateGalleryInput();

                    updateGalleryFileName();

                }
            );


            item.appendChild(
                image
            );


            item.appendChild(
                number
            );


            item.appendChild(
                removeButton
            );


            galleryPreview.appendChild(
                item
            );

        }
    );

}


function updateGalleryInput() {

    if (!galleryInput) {

        return;

    }


    const dataTransfer =
        new DataTransfer();


    selectedGalleryFiles.forEach(
        function (file) {

            dataTransfer.items.add(
                file
            );

        }
    );


    galleryInput.files =
        dataTransfer.files;

}

function updateGalleryFileName() {
  const fileNameElement = document.getElementById("galleryFileName");

  if (!fileNameElement) {
    return;
  }

  if (selectedGalleryFiles.length === 0) {
    fileNameElement.textContent = "No file chosen";

    return;
  }

  if (selectedGalleryFiles.length === 1) {
    fileNameElement.textContent = selectedGalleryFiles[0].name;

    return;
  }

  fileNameElement.textContent = selectedGalleryFiles
    .map(function (file) {
      return file.name;
    })
    .join(", ");
}


/* =========================================================
   VIDEOS
   ========================================================= */

const videoInput =
    document.getElementById(
        "galleryVideos"
    );


const videoPreview =
    document.getElementById(
        "videoPreview"
    );


let existingVideoCount = parseInt(page?.dataset.existingVideos || "0", 10);


const MAX_VIDEOS =
    2;


const MAX_VIDEO_SIZE =
    10 * 1024 * 1024;


let selectedVideoFiles =
    [];


if (
    videoInput &&
    videoPreview
) {

    videoInput.addEventListener(
        "change",
        function () {

            const files =
                Array.from(
                    this.files
                );


            const remainingSlots =
                Math.max(
                    0,
                    MAX_VIDEOS -
                    existingVideoCount -
                    selectedVideoFiles.length
                );


            if (
                files.length >
                remainingSlots
            ) {

                alert(
                    `You can add only ${remainingSlots} more video(s).`
                );

                updateVideoInput();

                return;

            }


            for (
                const file of files
            ) {

                if (
                    !file.type.startsWith(
                        "video/"
                    )
                ) {

                    alert(
                        "Only video files are allowed."
                    );

                    updateVideoInput();

                    return;

                }


                if (
                    file.size >
                    MAX_VIDEO_SIZE
                ) {

                    alert(
                        `"${file.name}" is larger than 10 MB.`
                    );

                    updateVideoInput();

                    return;

                }

            }


            selectedVideoFiles =
                selectedVideoFiles.concat(
                    files
                );


            renderVideoPreview();

            updateVideoInput();

            updateVideoFileName();

        }
    );

}


function renderVideoPreview() {

    if (!videoPreview) {

        return;

    }


    videoPreview.innerHTML =
        "";


    selectedVideoFiles.forEach(
        function (file, index) {

            const item =
                document.createElement(
                    "div"
                );


            item.className =
                "video-preview-item";


            const video =
                document.createElement(
                    "video"
                );


            const objectUrl =
                URL.createObjectURL(
                    file
                );


            video.src =
                objectUrl;


            video.controls =
                true;


            video.preload =
                "metadata";


            const number =
                document.createElement(
                    "div"
                );


            number.className =
                "gallery-preview-number";


            number.textContent =
                existingVideoCount +
                index +
                1;


            const removeButton =
                createRemoveButton(
                    "Remove video"
                );


            removeButton.addEventListener(
                "click",
                function () {

                    selectedVideoFiles =
                        selectedVideoFiles.filter(
                            function (
                                selectedFile
                            ) {

                                return (
                                    selectedFile !==
                                    file
                                );

                            }
                        );


                    URL.revokeObjectURL(
                        objectUrl
                    );


                    renderVideoPreview();

                    updateVideoInput();

                    updateVideoFileName();

                }
            );


            item.appendChild(
                video
            );


            item.appendChild(
                number
            );


            item.appendChild(
                removeButton
            );


            videoPreview.appendChild(
                item
            );

        }
    );

}


function updateVideoInput() {

    if (!videoInput) {

        return;

    }


    const dataTransfer =
        new DataTransfer();


    selectedVideoFiles.forEach(
        function (file) {

            dataTransfer.items.add(
                file
            );

        }
    );


    videoInput.files =
        dataTransfer.files;

}


function updateVideoFileName() {
  const fileNameElement = document.getElementById("videoFileName");

  if (!fileNameElement) {
    return;
  }

  if (selectedVideoFiles.length === 0) {
    fileNameElement.textContent = "No file chosen";

    return;
  }

  if (selectedVideoFiles.length === 1) {
    fileNameElement.textContent = selectedVideoFiles[0].name;

    return;
  }

  fileNameElement.textContent = selectedVideoFiles
    .map(function (file) {
      return file.name;
    })
    .join(", ");
}

/* =========================================================
   REMOVE BUTTON
   ========================================================= */

function createRemoveButton(
    ariaLabel
) {

    const button =
        document.createElement(
            "button"
        );


    button.type =
        "button";


    button.className =
        "media-preview-remove";


    button.setAttribute(
        "aria-label",
        ariaLabel
    );


    button.title =
        ariaLabel;


    button.innerHTML = `
        <span
            class="iconify"
            data-icon="solar:trash-bin-trash-bold"
        ></span>
    `;


    return button;

}

  /* =========================================================
       AVAILABILITY
       ========================================================= */

  const availableFrom = document.getElementById("availableFrom");

  const availableUntil = document.getElementById("availableUntil");

  if (availableFrom && availableUntil) {
    availableFrom.addEventListener("change", function () {
      availableUntil.min = this.value;

      if (availableUntil.value && availableUntil.value < this.value) {
        availableUntil.value = "";
      }
    });
  }

  /* =========================================================
       FORM SUBMIT
       ========================================================= */

  listingForm.addEventListener("submit", function (event) {
    const totalImages = existingGalleryCount + selectedGalleryFiles.length;

    if (totalImages > 8) {
      event.preventDefault();

      alert("A listing can have maximum 8 gallery images.");

      return;
    }

    const totalVideos = existingVideoCount + selectedVideoFiles.length;

    if (totalVideos > MAX_VIDEOS) {
      event.preventDefault();

      alert("A listing can have maximum 2 videos.");

      return;
    }

    for (const file of selectedVideoFiles) {
      if (file.size > MAX_VIDEO_SIZE) {
        event.preventDefault();

        alert(`"${file.name}" is larger than 10 MB.`);

        return;
      }
    }

    if (
      availableFrom &&
      availableUntil &&
      availableFrom.value &&
      availableUntil.value
    ) {
      if (availableUntil.value < availableFrom.value) {
        event.preventDefault();

        alert("Available Until cannot be before Available From.");

        availableUntil.focus();

        return;
      }
    }

    const saveButton = document.getElementById("saveListingBtn");

    if (saveButton) {
      saveButton.disabled = true;

      saveButton.classList.add("loading");
    }
  });

  /* =========================================================
       MESSAGE HELPER
       ========================================================= */

  function showMessage(container, message, type) {
    if (!container) {
      return;
    }

    const existing = container.querySelector(".js-form-message");

    if (existing) {
      existing.remove();
    }

    const messageElement = document.createElement("div");

    messageElement.className = `js-form-message ${type || ""}`;

    messageElement.textContent = message;

    container.prepend(messageElement);
  }


  /* =========================================================
   EXISTING MEDIA DELETE
   ========================================================= */

document.addEventListener("click", async function (event) {

    const coverButton =
        event.target.closest("#removeCurrentCover");

    if (coverButton) {

        event.preventDefault();

        const deleteUrl =
            coverButton.dataset.deleteUrl;

        if (!deleteUrl) {
            return;
        }

        if (!confirm("Remove this cover image?")) {
            return;
        }

        coverButton.disabled = true;

        try {

            const response = await fetch(
                deleteUrl,
                {
                    method: "POST",
                    headers: {
                        "X-CSRFToken":
                            listingForm.querySelector(
                                'input[name="csrfmiddlewaretoken"]'
                            ).value,

                        "X-Requested-With":
                            "XMLHttpRequest"
                    },
                    credentials: "same-origin"
                }
            );

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error("Delete failed.");
            }

            const coverWrapper =
                document.querySelector(
                    ".current-cover-wrapper"
                );

            if (coverWrapper) {
                coverWrapper.remove();
            }

        } catch (error) {

            console.error(error);

            alert(
                "Unable to remove the cover image."
            );

            coverButton.disabled = false;
        }

        return;
    }


    /* =====================================================
       EXISTING GALLERY / VIDEO DELETE
       ===================================================== */

    const deleteButton =
        event.target.closest(
            ".js-existing-delete-form button"
        );

    if (!deleteButton) {
        return;
    }

    event.preventDefault();

    const form =
        deleteButton.closest(
            ".js-existing-delete-form"
        );

    if (!form) {
        return;
    }

    if (!confirm("Delete this media?")) {
        return;
    }

    deleteButton.disabled = true;

    try {

        const response = await fetch(
            form.action,
            {
                method: "POST",

                headers: {
                    "X-CSRFToken":
                        listingForm.querySelector(
                            'input[name="csrfmiddlewaretoken"]'
                        ).value,

                    "X-Requested-With":
                        "XMLHttpRequest"
                },

                credentials: "same-origin"
            }
        );

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error("Delete failed.");
        }


        /* REMOVE ONLY THE CLICKED ITEM */

        const mediaItem =
            form.closest(
                "[data-media-item]"
            );

        if (mediaItem) {
            mediaItem.remove();
        }


        /* UPDATE COUNTS */

        if (
            form.action.includes("/images/")
        ) {

            existingGalleryCount--;

        } else if (
            form.action.includes("/video/")
        ) {

            existingVideoCount--;
        }


    } catch (error) {

        console.error(error);

        alert(
            "Unable to delete this media."
        );

        deleteButton.disabled = false;
    }

});
});


/* =========================================================
   DATE PICKERS
   - past dates cannot be picked (min = today)
   - "until" can never be before its "from"  (data-range groups)
   Server side validates the same rules.
   ========================================================= */

(function () {
  function pad(number) {
    return String(number).padStart(2, "0");
  }

  function todayString() {
    const now = new Date();

    return (
      now.getFullYear() + "-" + pad(now.getMonth() + 1) + "-" + pad(now.getDate())
    );
  }

  function initDatePickers() {
    const today = todayString();

    document.querySelectorAll('input[type="date"]').forEach(function (input) {
      input.min = today;
    });

    const groups = {};

    document.querySelectorAll("[data-range]").forEach(function (input) {
      const name = input.getAttribute("data-range");
      const role = input.getAttribute("data-range-role");

      groups[name] = groups[name] || {};
      groups[name][role] = input;
    });

    Object.keys(groups).forEach(function (name) {
      const start = groups[name].start;
      const end = groups[name].end;

      if (!start || !end) {
        return;
      }

      function syncEnd(clearInvalid) {
        let minimum = today;

        if (start.value && start.value > minimum) {
          minimum = start.value;
        }

        end.min = minimum;

        if (clearInvalid && end.value && end.value < minimum) {
          end.value = "";
        }
      }

      start.addEventListener("change", function () {
        syncEnd(true);
      });

      /* on page load only restrict the calendar, keep saved values */
      syncEnd(false);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initDatePickers);
  } else {
    initDatePickers();
  }
})();