(function () {
  const input = document.getElementById("photo-input");
  if (!input) return;

  const photoUpload = document.getElementById("photo-upload");
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

  canvas.width = VIEW;
  canvas.height = VIEW;

  let img = null;
  let minScale = 1;
  let scale = 1;
  let offsetX = 0;
  let offsetY = 0;
  let dragging = false;
  let dragStart = null;

  input.addEventListener("change", () => {
    const file = input.files[0];
    if (!file) return;
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

  canvas.addEventListener("pointerdown", (e) => {
    dragging = true;
    dragStart = { x: e.clientX - offsetX, y: e.clientY - offsetY };
    canvas.setPointerCapture(e.pointerId);
    canvas.style.cursor = "grabbing";
  });

  canvas.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    offsetX = e.clientX - dragStart.x;
    offsetY = e.clientY - dragStart.y;
    draw();
  });

  canvas.addEventListener("pointerup", () => {
    dragging = false;
    canvas.style.cursor = "grab";
  });

  zoomSlider.addEventListener("input", () => {
    const newScale = minScale * parseFloat(zoomSlider.value);
    // Zoom around the viewport's center point rather than its top-left
    // corner, so the subject under the middle of the frame stays put.
    const centerImgX = (VIEW / 2 - offsetX) / scale;
    const centerImgY = (VIEW / 2 - offsetY) / scale;
    scale = newScale;
    offsetX = VIEW / 2 - centerImgX * scale;
    offsetY = VIEW / 2 - centerImgY * scale;
    draw();
  });

  cancelBtn.addEventListener("click", () => {
    stage.hidden = true;
    input.value = "";
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

    out.toBlob((blob) => {
      const file = new File([blob], "photo.jpg", { type: "image/jpeg" });
      const dt = new DataTransfer();
      dt.items.add(file);
      photoUpload.files = dt.files;

      photoPreview.innerHTML = "";
      const previewImg = document.createElement("img");
      previewImg.className = "thumb-large";
      previewImg.src = URL.createObjectURL(blob);
      photoPreview.appendChild(previewImg);

      stage.hidden = true;
      input.value = "";
    }, "image/jpeg", 0.9);
  });
})();
