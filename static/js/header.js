document.addEventListener("DOMContentLoaded", function () {

    const header = document.querySelector(".site-header");
    const menuToggle = document.querySelector(".menu-toggle");

    if (!header || !menuToggle) {
        return;
    }


    menuToggle.addEventListener("click", function () {

        const isOpen = header.classList.toggle("menu-open");

        menuToggle.setAttribute(
            "aria-expanded",
            isOpen ? "true" : "false"
        );

        menuToggle.setAttribute(
            "aria-label",
            isOpen
                ? "Close navigation"
                : "Open navigation"
        );

    });

});