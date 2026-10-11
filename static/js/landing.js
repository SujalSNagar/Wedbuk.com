document.addEventListener("DOMContentLoaded", function () {
  /* ========================================================
       SCROLL REVEAL ANIMATION
       ======================================================== */

  const revealElements = document.querySelectorAll(".reveal-on-scroll");

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");

            observer.unobserve(entry.target);
          }
        });
      },
      {
        threshold: 0.12,
      },
    );

    revealElements.forEach(function (element) {
      observer.observe(element);
    });
  } else {
    revealElements.forEach(function (element) {
      element.classList.add("is-visible");
    });
  }

  /* ========================================================
       STAGGER CARD ANIMATION
       ======================================================== */

  const animatedGroups = [
    ".city-grid .reveal-on-scroll",
    ".budget-grid .reveal-on-scroll",
    ".event-type-grid .reveal-on-scroll",
    ".package-home-grid .reveal-on-scroll",
    ".trending-grid .reveal-on-scroll",
    ".function-grid .reveal-on-scroll",
    ".why-grid .reveal-on-scroll",
    ".testimonial-grid .reveal-on-scroll",
  ];

  animatedGroups.forEach(function (selector) {
    const elements = document.querySelectorAll(selector);

    elements.forEach(function (element, index) {
      element.style.transitionDelay = `${index * 80}ms`;
    });
  });

  /* ========================================================
       HERO IMAGE FLOATING EFFECT
       ======================================================== */

  const heroGallery = document.querySelector(".hero-gallery");

  if (heroGallery) {
    window.addEventListener(
      "scroll",
      function () {
        const scrollY = window.scrollY;

        if (scrollY > 700) {
          return;
        }

        const imageOne = heroGallery.querySelector(".hero-img-1");

        const imageTwo = heroGallery.querySelector(".hero-img-2");

        const imageThree = heroGallery.querySelector(".hero-img-3");

        if (imageOne) {
          imageOne.style.transform = `translateY(${scrollY * 0.035}px)`;
        }

        if (imageTwo) {
          imageTwo.style.transform = `translateY(${scrollY * -0.02}px)`;
        }

        if (imageThree) {
          imageThree.style.transform = `translateY(${scrollY * 0.025}px)`;
        }
      },
      {
        passive: true,
      },
    );
  }

  /* ========================================================
       HERO SEARCH
       ======================================================== */

  const searchForm = document.getElementById("vendor-search");

  const cityInput = document.getElementById("city-input");

  if (searchForm && cityInput) {
    searchForm.addEventListener("submit", function () {
      const city = cityInput.value.trim();

      if (!city) {
        return;
      }
    });
  }

  /* ========================================================
       BUDGET PLANNER
       Frontend only for now
       ======================================================== */

  const budgetInput = document.getElementById("weddingBudget");

  const budgetRange = document.getElementById("weddingBudgetRange");

  if (budgetInput && budgetRange) {
    function formatIndianCurrency(value) {
      return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0,
      }).format(value);
    }

    function updateBudgetPlanner(value) {
      const budget = Number(value) || 0;

      const venue = budget * 0.3;

      const catering = budget * 0.25;

      const decoration = budget * 0.15;

      const photography = budget * 0.1;

      const makeup = budget * 0.08;

      const other = budget * 0.12;

      const venueElement = document.getElementById("budgetVenue");

      const cateringElement = document.getElementById("budgetCatering");

      const decorationElement = document.getElementById("budgetDecoration");

      const photographyElement = document.getElementById("budgetPhotography");

      const makeupElement = document.getElementById("budgetMakeup");

      const otherElement = document.getElementById("budgetOther");

      if (venueElement) {
        venueElement.textContent = formatIndianCurrency(venue);
      }

      if (cateringElement) {
        cateringElement.textContent = formatIndianCurrency(catering);
      }

      if (decorationElement) {
        decorationElement.textContent = formatIndianCurrency(decoration);
      }

      if (photographyElement) {
        photographyElement.textContent = formatIndianCurrency(photography);
      }

      if (makeupElement) {
        makeupElement.textContent = formatIndianCurrency(makeup);
      }

      if (otherElement) {
        otherElement.textContent = formatIndianCurrency(other);
      }

      const totalElement = document.getElementById("budgetTotal");

      if (totalElement) {
        totalElement.textContent = formatIndianCurrency(budget);
      }
    }

    budgetInput.addEventListener("input", function () {
      const value = Number(this.value) || 0;

      budgetRange.value = value;

      updateBudgetPlanner(value);
    });

    budgetRange.addEventListener("input", function () {
      const value = Number(this.value) || 0;

      budgetInput.value = value;

      updateBudgetPlanner(value);
    });

    updateBudgetPlanner(Number(budgetInput.value) || 500000);
  }

  /* ========================================================
       SMOOTH ANCHOR SCROLL
       ======================================================== */

  const anchorLinks = document.querySelectorAll('a[href^="#"]');

  anchorLinks.forEach(function (link) {
    link.addEventListener("click", function (event) {
      const targetId = this.getAttribute("href");

      if (!targetId || targetId === "#") {
        return;
      }

      const target = document.querySelector(targetId);

      if (target) {
        event.preventDefault();

        target.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    });
  });
});

