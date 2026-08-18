(function () {
  const input = document.getElementById("photo-input");
  if (!input) return;

  const form = input.closest("form");
  const photoPreview = document.getElementById("photo-preview");
  const stage = document.getElementById("crop-stage");
  const canvas = document.getElementById("crop-canvas");
  const zoomSlider = document.getElementById("crop-zoom");
  const saveBtn = document.getElementById("crop-save");
  const cancelBtn = document.getElementById("crop-cancel");
  const ctx = canvas.getContext("2d");
  const deleteBtn = document.getElementById("photo-delete-btn");

  if (deleteBtn) {
    deleteBtn.addEventListener("click", async () => {
      if (!confirm("Delete this photo?")) return;
      const itemId = deleteBtn.dataset.itemId;
      await fetch(`/admin/items/${itemId}/photo/delete`, { method: "POST" });
      window.location.reload();
    });
  }

  const VIEW = 280; // on-screen crop viewport, square
  const OUTPUT = 400; // saved photo size
  const MAX_ZOOM = 3; // matches the slider's max

  canvas.width = VIEW;
  canvas.height = VIEW;

  let img = null;
  let minScale = 1;
  let scale = 1;
  let offsetX = 0;
  let offsetY = 0;

  // Cropped photo waiting to be attached to the save request. Bypasses
  // <input type="file"> + DataTransfer entirely (see saveBtn handler) -
  // that combo has an inconsistent support/behavior history on iOS
  // Safari and was silently failing on iPad.
  let pendingPhotoBlob = null;

  input.addEventListener("change", () => {
    const file = input.files[0];
    if (!file) return;
    pendingPhotoBlob = null;
    const reader = new FileReader();
    reader.onload = (e) => {
      img = new Image();
      img.onload = onImageLoaded;
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  });

  function onImageLoaded() {
    // "Cover" scale: the smallest zoom where the image still fills the
    // square viewport with no gaps, then centered.
    minScale = Math.max(VIEW / img.width, VIEW / img.height);
    scale = minScale;
    offsetX = (VIEW - img.width * scale) / 2;
    offsetY = (VIEW - img.height * scale) / 2;
    zoomSlider.value = "1";
    draw();
    stage.hidden = false;
  }

  function clampOffsets() {
    const minX = VIEW - img.width * scale;
    const minY = VIEW - img.height * scale;
    offsetX = Math.min(0, Math.max(minX, offsetX));
    offsetY = Math.min(0, Math.max(minY, offsetY));
  }

  function draw() {
    clampOffsets();
    ctx.clearRect(0, 0, VIEW, VIEW);
    ctx.drawImage(img, offsetX, offsetY, img.width * scale, img.height * scale);
  }

  // Sets zoom while keeping a given viewport point (in VIEW coordinates)
  // anchored under the same spot on the image - shared by the slider and
  // pinch-to-zoom so both feel the same.
  function setScale(newScale, anchorX, anchorY) {
    const imgX = (anchorX - offsetX) / scale;
    const imgY = (anchorY - offsetY) / scale;
    scale = Math.min(Math.max(newScale, minScale), minScale * MAX_ZOOM);
    offsetX = anchorX - imgX * scale;
    offsetY = anchorY - imgY * scale;
    draw();
  }

  function canvasPoint(clientX, clientY) {
    const rect = canvas.getBoundingClientRect();
    return {
      x: (clientX - rect.left) * (VIEW / rect.width),
      y: (clientY - rect.top) * (VIEW / rect.height),
    };
  }

  // ---- Mouse drag (desktop/dev testing) ----
  let mouseDragging = false;
  let mouseDragStart = null;

  canvas.addEventListener("mousedown", (e) => {
    mouseDragging = true;
    mouseDragStart = { x: e.clientX - offsetX, y: e.clientY - offsetY };
    canvas.style.cursor = "grabbing";
  });
  window.addEventListener("mousemove", (e) => {
    if (!mouseDragging) return;
    offsetX = e.clientX - mouseDragStart.x;
    offsetY = e.clientY - mouseDragStart.y;
    draw();
  });
  window.addEventListener("mouseup", () => {
    mouseDragging = false;
    canvas.style.cursor = "grab";
  });

  // ---- Touch drag + pinch-to-zoom (iPad/mobile) ----
  // Raw Touch events with explicit preventDefault, not Pointer events -
  // iOS Safari has a history of letting its own scroll/gesture
  // recognizer win over Pointer events on canvas drags even with
  // touch-action: none set, which is what was blocking panning.
  let touchMode = null; // "pan" | "pinch"
  let panStart = null;
  let pinchStartDist = null;
  let pinchStartScale = null;
  let pinchAnchor = null;

  canvas.addEventListener(
    "touchstart",
    (e) => {
      e.preventDefault();
      if (e.touches.length === 1) {
        touchMode = "pan";
        const p = canvasPoint(e.touches[0].clientX, e.touches[0].clientY);
        panStart = { x: p.x - offsetX, y: p.y - offsetY };
      } else if (e.touches.length === 2) {
        touchMode = "pinch";
        const p1 = canvasPoint(e.touches[0].clientX, e.touches[0].clientY);
        const p2 = canvasPoint(e.touches[1].clientX, e.touches[1].clientY);
        pinchStartDist = Math.max(Math.hypot(p2.x - p1.x, p2.y - p1.y), 1);
        pinchStartScale = scale;
        pinchAnchor = { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 };
      }
    },
    { passive: false }
  );

  canvas.addEventListener(
    "touchmove",
    (e) => {
      e.preventDefault();
      if (touchMode === "pan" && e.touches.length === 1) {
        const p = canvasPoint(e.touches[0].clientX, e.touches[0].clientY);
        offsetX = p.x - panStart.x;
        offsetY = p.y - panStart.y;
        draw();
      } else if (touchMode === "pinch" && e.touches.length === 2) {
        const p1 = canvasPoint(e.touches[0].clientX, e.touches[0].clientY);
        const p2 = canvasPoint(e.touches[1].clientX, e.touches[1].clientY);
        const dist = Math.hypot(p2.x - p1.x, p2.y - p1.y);
        setScale(pinchStartScale * (dist / pinchStartDist), pinchAnchor.x, pinchAnchor.y);
        zoomSlider.value = String(scale / minScale);
      }
    },
    { passive: false }
  );

  canvas.addEventListener(
    "touchend",
    (e) => {
      e.preventDefault();
      if (e.touches.length === 1) {
        // Dropped from two fingers to one - restart as a pan from here
        // instead of jumping using the stale pinch anchor.
        touchMode = "pan";
        const p = canvasPoint(e.touches[0].clientX, e.touches[0].clientY);
        panStart = { x: p.x - offsetX, y: p.y - offsetY };
      } else if (e.touches.length === 0) {
        touchMode = null;
      }
    },
    { passive: false }
  );

  zoomSlider.addEventListener("input", () => {
    setScale(minScale * parseFloat(zoomSlider.value), VIEW / 2, VIEW / 2);
  });

  cancelBtn.addEventListener("click", () => {
    stage.hidden = true;
    input.value = "";
    pendingPhotoBlob = null;
  });

  saveBtn.addEventListener("click", () => {
    const outFactor = OUTPUT / VIEW;
    const outScale = scale * outFactor;
    const outX = offsetX * outFactor;
    const outY = offsetY * outFactor;

    const out = document.createElement("canvas");
    out.width = OUTPUT;
    out.height = OUTPUT;
    out.getContext("2d").drawImage(img, outX, outY, img.width * outScale, img.height * outScale);

    // toDataURL is synchronous and far more reliable than toBlob() on
    // iOS Safari, where toBlob's callback can silently never fire.
    const dataUrl = out.toDataURL("image/jpeg", 0.9);
    pendingPhotoBlob = dataUrlToBlob(dataUrl);

    photoPreview.innerHTML = "";
    const previewImg = document.createElement("img");
    previewImg.className = "thumb-large";
    previewImg.src = dataUrl;
    photoPreview.appendChild(previewImg);

    stage.hidden = true;
    input.value = "";
  });

  function dataUrlToBlob(dataUrl) {
    const [header, base64] = dataUrl.split(",");
    const mime = header.match(/:(.*?);/)[1];
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return new Blob([bytes], { type: mime });
  }

  // Only intercepted when a photo was actually cropped this session -
  // otherwise the form posts normally and the backend just leaves the
  // existing photo (or lack of one) untouched.
  if (form) {
    form.addEventListener("submit", (e) => {
      if (!pendingPhotoBlob) return;
      e.preventDefault();

      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) submitBtn.disabled = true;

      const formData = new FormData(form);
      formData.set("photo", pendingPhotoBlob, "photo.jpg");

      fetch(form.action, { method: "POST", body: formData })
        .then((res) => {
          if (!res.ok) throw new Error(`Server returned ${res.status}`);
          window.location.href = res.url;
        })
        .catch((err) => {
          alert(`Couldn't save photo: ${err.message}`);
          if (submitBtn) submitBtn.disabled = false;
        });
    });
  }
})();
