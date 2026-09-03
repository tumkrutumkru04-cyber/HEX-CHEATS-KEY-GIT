let selectedDuration = "30_days";

const durationGrid = document.getElementById("durationGrid");
const customDurationRow = document.getElementById("customDurationRow");
const customHoursGroup = document.getElementById("customHoursGroup");
const customDaysGroup = document.getElementById("customDaysGroup");

durationGrid.addEventListener("click", (e) => {
  const opt = e.target.closest(".duration-option");
  if (!opt) return;
  document.querySelectorAll(".duration-option").forEach((el) => el.classList.remove("selected"));
  opt.classList.add("selected");
  selectedDuration = opt.dataset.value;

  const isCustomHours = selectedDuration === "custom_hours";
  const isCustomDays = selectedDuration === "custom_days";
  customDurationRow.style.display = (isCustomHours || isCustomDays) ? "grid" : "none";
  customHoursGroup.style.display = isCustomHours ? "flex" : "none";
  customDaysGroup.style.display = isCustomDays ? "flex" : "none";
});

document.getElementById("generateForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("generateBtn");
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner"></span> Generating…`;

  const body = {
    quantity: parseInt(document.getElementById("quantity").value, 10),
    prefix: document.getElementById("prefix").value.trim() || "HEX",
    duration_type: selectedDuration,
    note: document.getElementById("note").value.trim() || null,
  };
  if (selectedDuration === "custom_hours") {
    body.custom_hours = parseInt(document.getElementById("customHours").value, 10);
  }
  if (selectedDuration === "custom_days") {
    body.custom_days = parseInt(document.getElementById("customDays").value, 10);
  }

  try {
    const data = await apiFetch("/admin/api/keys/generate", {
      method: "POST",
      body: JSON.stringify(body),
    });
    showToast(`${data.created.length} key(s) generated.`);
    renderResults(data.created);
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate Keys";
  }
});

function renderResults(keys) {
  const panel = document.getElementById("resultPanel");
  const box = document.getElementById("generatedKeysBox");
  panel.style.display = "block";
  box.innerHTML = keys.map((k) => `<div class="key-line"><span>${k.license_key}</span><span class="text-muted">${k.duration_label}</span></div>`).join("");
  panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

document.getElementById("copyAllBtn").addEventListener("click", () => {
  const lines = Array.from(document.querySelectorAll(".key-line span:first-child")).map((el) => el.textContent);
  navigator.clipboard.writeText(lines.join("\n")).then(() => showToast("Copied to clipboard."));
});
