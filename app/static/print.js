(function () {
  const appEl = document.querySelector(".app");
  const initialsEl = document.getElementById("initials");
  const toast = document.getElementById("toast");
  const today = appEl.dataset.today;

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

  function expirationFor(shelfLifeDays) {
    if (!shelfLifeDays) return "";
    const prepped = new Date(today + "T00:00:00");
    prepped.setDate(prepped.getDate() + parseInt(shelfLifeDays, 10));
    return prepped.toISOString().slice(0, 10);
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

      const body = new URLSearchParams({
        food_name: card.dataset.name,
        initials: name,
        prepped_date: today,
        expiration_date: expirationFor(card.dataset.shelfLife),
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
