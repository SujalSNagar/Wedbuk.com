document.addEventListener("DOMContentLoaded", function () {
  const mainImage = document.getElementById("mainListingImage");
  const thumbnails = document.querySelectorAll(".listing-thumbnail");

  const openGallery = document.getElementById("openGallery");
  const lightbox = document.getElementById("listingLightbox");
  const lightboxImage = document.getElementById("lightboxImage");
  const closeGallery = document.getElementById("closeGallery");

  /* =====================================================
       THUMBNAIL SWITCHING
       ===================================================== */

  thumbnails.forEach(function (thumbnail) {
    thumbnail.addEventListener("click", function () {
      const imageUrl = this.dataset.image;

      if (!imageUrl || !mainImage) {
        return;
      }

      mainImage.src = imageUrl;

      thumbnails.forEach(function (item) {
        item.classList.remove("active");
      });

      this.classList.add("active");
    });
  });

  /* =====================================================
       OPEN LIGHTBOX
       ===================================================== */

  if (openGallery && lightbox && lightboxImage && mainImage) {
    openGallery.addEventListener("click", function () {
      lightboxImage.src = mainImage.src;

      lightbox.classList.add("show");

      document.body.style.overflow = "hidden";
    });
  }

  /* =====================================================
       CLOSE LIGHTBOX
       ===================================================== */

  function closeLightbox() {
    if (!lightbox) {
      return;
    }

    lightbox.classList.remove("show");

    document.body.style.overflow = "";
  }

  if (closeGallery) {
    closeGallery.addEventListener("click", closeLightbox);
  }

  if (lightbox) {
    lightbox.addEventListener("click", function (event) {
      if (event.target === lightbox) {
        closeLightbox();
      }
    });
  }

  /* =====================================================
       ESCAPE KEY
       ===================================================== */

  document.addEventListener("keydown", function (event) {
    if (
      event.key === "Escape" &&
      lightbox &&
      lightbox.classList.contains("show")
    ) {
      closeLightbox();
    }
  });
});
