/* LLM actions dropdown (works with instant loading via event delegation) */

/* Toggle dropdown via arrow */
document.addEventListener("click", function(e) {
  var toggle = e.target.closest("[data-llm-toggle]");
  if (toggle) {
    var dropdown = toggle.closest(".llm-dropdown");
    dropdown.classList.toggle("llm-dropdown--open");
    e.stopPropagation();
    return;
  }

  /* Close on outside click */
  var open = document.querySelectorAll(".llm-dropdown--open");
  for (var i = 0; i < open.length; i++) {
    open[i].classList.remove("llm-dropdown--open");
  }
});

/* Copy markdown on button click */
document.addEventListener("click", function(e) {
  var btn = e.target.closest("[data-copy-md]");
  if (!btn) return;

  var url = btn.getAttribute("data-copy-md");
  var label = btn.querySelector(".llm-dropdown__label");

  fetch(url)
    .then(function(r) { return r.text(); })
    .then(function(text) {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        return navigator.clipboard.writeText(text);
      }
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    })
    .then(function() {
      if (label) {
        label.textContent = "Copied!";
        setTimeout(function() { label.textContent = "Copy page"; }, 1500);
      }
    })
    .catch(function(err) { console.error("Copy failed:", err); });
});

/* Close dropdown when clicking a menu item */
document.addEventListener("click", function(e) {
  var item = e.target.closest(".llm-dropdown__item");
  if (item) {
    var dropdown = item.closest(".llm-dropdown");
    if (dropdown) dropdown.classList.remove("llm-dropdown--open");
  }
});
