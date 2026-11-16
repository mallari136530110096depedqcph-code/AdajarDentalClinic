document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".flash").forEach((message) => {
    window.setTimeout(() => {
      message.style.transition = "opacity .4s";
      message.style.opacity = "0";
      window.setTimeout(() => message.remove(), 450);
    }, 6000);
  });
});
