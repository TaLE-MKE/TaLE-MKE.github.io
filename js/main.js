/* TaLE MKE: minimal vanilla JS (nav toggle, footer year, contact form). */
(function () {
  "use strict";

  document.documentElement.classList.remove("no-js");

  /* ---------- Mobile navigation ---------- */
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("site-nav");

  if (toggle && nav) {
    var setOpen = function (open) {
      toggle.setAttribute("aria-expanded", String(open));
      nav.classList.toggle("is-open", open);
    };

    toggle.addEventListener("click", function () {
      setOpen(toggle.getAttribute("aria-expanded") !== "true");
    });

    // Escape closes the menu and returns focus to the toggle.
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") {
        setOpen(false);
        toggle.focus();
      }
    });

    // Close if the viewport grows past the mobile breakpoint.
    window.matchMedia("(min-width: 901px)").addEventListener("change", function (mq) {
      if (mq.matches) setOpen(false);
    });
  }

  /* ---------- Footer year ---------- */
  var year = document.getElementById("year");
  if (year) year.textContent = String(new Date().getFullYear());

  /* ---------- Contact form (front end only) ----------
     ======================================================================
     WIRE IN A FORM HANDLER HERE
     This site has no backend. To receive messages, sign up for a form
     service (for example Formspree: https://formspree.io), create a form,
     and paste its endpoint below, e.g.
       var FORM_ENDPOINT = "https://formspree.io/f/abcdwxyz";
     Also set the same URL in the <form action="..."> attribute in
     contact.html so the form still submits if JavaScript is off.
     While FORM_ENDPOINT is empty, the form validates input and shows a
     notice, but nothing is sent anywhere.
     ====================================================================== */
  var FORM_ENDPOINT = "";

  var form = document.getElementById("contact-form");
  if (!form) return;

  var status = document.getElementById("form-status");
  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  var rules = {
    name: function (v) { return v ? "" : "Please enter your name."; },
    email: function (v) {
      if (!v) return "Please enter your email address.";
      return EMAIL_RE.test(v) ? "" : "Please enter a valid email address, like name@example.com.";
    },
    message: function (v) { return v ? "" : "Please enter a message."; }
  };

  function validateField(input) {
    var msg = rules[input.name](input.value.trim());
    var err = document.getElementById(input.id + "-error");
    input.setAttribute("aria-invalid", msg ? "true" : "false");
    if (err) err.textContent = msg;
    return !msg;
  }

  function showStatus(text, kind) {
    status.textContent = text;
    status.className = "form-status " + (kind === "error" ? "is-error" : "is-success");
  }

  Object.keys(rules).forEach(function (name) {
    var input = form.elements[name];
    input.addEventListener("blur", function () {
      if (input.value.trim()) validateField(input);
    });
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    status.textContent = "";
    status.className = "form-status";

    var firstInvalid = null;
    Object.keys(rules).forEach(function (name) {
      var input = form.elements[name];
      if (!validateField(input) && !firstInvalid) firstInvalid = input;
    });
    if (firstInvalid) {
      firstInvalid.focus();
      return;
    }

    if (!FORM_ENDPOINT) {
      showStatus(
        "Thanks! This form is not connected yet, so your message was not sent. " +
        "Please email us directly using the address on this page.",
        "success"
      );
      return;
    }

    var button = form.querySelector("button[type=submit]");
    button.disabled = true;

    fetch(FORM_ENDPOINT, {
      method: "POST",
      body: new FormData(form),
      headers: { Accept: "application/json" }
    })
      .then(function (res) {
        if (!res.ok) throw new Error("Request failed");
        form.reset();
        showStatus("Thanks! Your message was sent. We will get back to you soon.", "success");
      })
      .catch(function () {
        showStatus("Sorry, something went wrong. Please email us directly instead.", "error");
      })
      .then(function () { button.disabled = false; });
  });
})();
