(function () {
  const initialsEl = document.getElementById("initials");
  const toast = document.getElementById("toast");

  const savedInitials = localStorage.getItem("labelprinter_initials");
  if (savedInitials) initialsEl.value = savedInitials;

  let toastTimer = null;

  function showToast(message, isError) {
    toast.textContent = message;
    toast.hidden = false;
    toast.classList.toggle("toast-error", isError);
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toast.hidden = true;
    }, 2500);
  }

  document.querySelectorAll(".print-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const card = btn.closest(".card");
      const name = initialsEl.value.trim();

      if (!name) {
        showToast("Enter your name first", true);
        return;
      }
      localStorage.setItem("labelprinter_initials", name);

      // No dates are sent: the server stamps prep/use-by from its own clock
      // when the label is printed, so a screen left open for days still
      // prints today's date.
      const body = new URLSearchParams({
        food_name: card.dataset.name,
        initials: name,
      });

      try {
        const res = await fetch("/print", { method: "POST", body });
        const data = await res.json();
        if (data.error) {
          showToast(data.error, true);
        } else {
          showToast("Printed: " + card.dataset.name, false);
        }
      } catch (err) {
        showToast("Could not reach the server", true);
      }
    });
  });
})();
