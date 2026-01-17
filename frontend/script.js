function setupUpload(boxId, previewId) {
  const box = document.getElementById(boxId);
  const input = box.querySelector("input");
  const preview = document.getElementById(previewId);

  box.addEventListener("click", () => input.click());

  box.addEventListener("dragover", e => {
    e.preventDefault();
    box.style.borderColor = "#3ddc97";
  });

  box.addEventListener("dragleave", () => {
    box.style.borderColor = "#30363d";
  });

  box.addEventListener("drop", e => {
    e.preventDefault();
    input.files = e.dataTransfer.files;
    handlePreview(input, preview);
    box.style.borderColor = "#30363d";
  });

  input.addEventListener("change", () => handlePreview(input, preview));
}

function handlePreview(input, preview) {
  preview.innerHTML = "";
  const file = input.files[0];
  if (!file) return;

  const img = document.createElement("img");
  img.src = URL.createObjectURL(file);
  preview.appendChild(img);
}

// Init uploads
setupUpload("holdUpload", "holdPreview");
setupUpload("wallUpload", "wallPreview");
