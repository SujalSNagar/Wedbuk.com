document.addEventListener("DOMContentLoaded", function () {
  const section = document.querySelector("#wedbook-video-story");

  if (!section) {
    return;
  }

  const video = section.querySelector(".wedbook-story-video");

  const stories = Array.from(section.querySelectorAll(".wedbook-story-text"));

  const progressBar = section.querySelector(".wedbook-video-progress span");

  const scrollIndicator = section.querySelector(".wedbook-scroll-indicator");

  if (!video || !stories.length) {
    return;
  }

  /* =====================================================
       LAZY LOAD VIDEO
       ===================================================== */

  let videoLoaded = false;

  function loadVideo() {
    if (videoLoaded) {
      return;
    }

    const source = video.querySelector("source[data-src]");

    if (!source) {
      return;
    }

    source.src = source.dataset.src;

    video.load();

    videoLoaded = true;

    video.play().catch(function () {
      // Autoplay can be blocked by some browsers.
    });
  }

  if ("IntersectionObserver" in window) {
    const videoObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            loadVideo();

            videoObserver.unobserve(section);
          }
        });
      },
      {
        rootMargin: "300px 0px",
      },
    );

    videoObserver.observe(section);
  } else {
    loadVideo();
  }

  /* =====================================================
       STORY SCROLL ANIMATION
       ===================================================== */

  let currentStep = -1;

  function updateStory() {
    const rect = section.getBoundingClientRect();

    const sectionHeight = section.offsetHeight - window.innerHeight;

    if (sectionHeight <= 0) {
      return;
    }

    /*
     * 0 → section top
     * 1 → section bottom
     */

    let progress = -rect.top / sectionHeight;

    progress = Math.max(0, Math.min(1, progress));

    /* -------------------------------------------------
           Progress bar
           ------------------------------------------------- */

    if (progressBar) {
      progressBar.style.height = `${progress * 100}%`;
    }

    /* -------------------------------------------------
           Story step
           ------------------------------------------------- */

    const totalSteps = stories.length;

    let step = Math.floor(progress * totalSteps);

    if (step >= totalSteps) {
      step = totalSteps - 1;
    }

    if (step !== currentStep) {
      stories.forEach(function (story, index) {
        story.classList.toggle("active", index === step);
      });

      currentStep = step;
    }

    /* -------------------------------------------------
           Scroll indicator
           ------------------------------------------------- */

    if (scrollIndicator) {
      if (progress > 0.04) {
        scrollIndicator.style.opacity = "0";
      } else {
        scrollIndicator.style.opacity = "1";
      }
    }
  }

  let ticking = false;

  function requestUpdate() {
    if (!ticking) {
      window.requestAnimationFrame(function () {
        updateStory();

        ticking = false;
      });

      ticking = true;
    }
  }

  window.addEventListener("scroll", requestUpdate, { passive: true });

  window.addEventListener("resize", requestUpdate);

  /* Initial state */

  updateStory();
});
