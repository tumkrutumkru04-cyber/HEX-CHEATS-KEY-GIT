let currentPage = 1;
const pageSize = 20;

const searchInput = document.getElementById("searchInput");
const statusFilter = document.getElementById("statusFilter");
const keysBody = document.getElementById("keysBody");
const paginationInfo = document.getElementById("paginationInfo");
const pageIndicator = document.getElementById("pageIndicator");
const prevPageBtn = document.getElementById("prevPageBtn");
const nextPageBtn = document.getElementById("nextPageBtn");

async function loadKeys() {
  keysBody.innerHTML = `<tr class="loading-row"><td colspan="7"><div class="spinner" style="margin:0 auto;"></div></td></tr>`;

  const params = new URLSearchParams({
    page: currentPage,
    page_size: pageSize,
  });
  if (searchInput.value.trim()) params.set("search", searchInput.value.trim());
  if (statusFilter.value !== "ALL") params.set("status", statusFilter.value);

  try {
    const data = await apiFetch(`/admin/api/keys?${params.toString()}`);
    if (!data) return;
    renderKeys(data);
  } catch (err) {
    keysBody.innerHTML = `<tr><td colspan="7" class="empty-state">Failed to load keys</td></tr>`;
    showToast(err.message, "error");
  }
}

function renderKeys(data) {
  if (data.items.length === 0) {
    keysBody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><div class="empty-state-icon">🔑</div>No license keys found</div></td></tr>`;
  } else {
    keysBody.innerHTML = data.items.map((lic) => `
      <tr data-id="${lic.id}">
        <td class="mono">${lic.license_key}</td>
        <td>${statusBadge(lic.is_expired && lic.status === "ACTIVE" ? "EXPIRED" : lic.status)}</td>
        <td class="text-secondary">${lic.duration_label || "—"}</td>
        <td>${lic.device_count}</td>
        <td class="text-muted">${lic.expires_at ? formatDate(lic.expires_at) : "Lifetime"}</td>
        <td class="text-muted">${formatDate(lic.created_at)}</td>
        <td>
          <div class="row-actions">
            <button class="icon-btn" title="Activate" onclick="doAction('activate','${lic.id}')">✓</button>
            <button class="icon-btn" title="Deactivate" onclick="doAction('deactivate','${lic.id}')">⏸</button>
            <button class="icon-btn" title="Ban" onclick="doAction('ban','${lic.id}')">⛔</button>
            <button class="icon-btn" title="Extend +7 days" onclick="doExtend('${lic.id}')">+7d</button>
            <button class="icon-btn" title="Reset device" onclick="doAction('reset-device','${lic.id}')">↺</button>
            <button class="icon-btn" title="Delete" onclick="doDelete('${lic.id}')">🗑</button>
          </div>
        </td>
      </tr>
    `).join("");
  }

  const start = data.total === 0 ? 0 : (data.page - 1) * data.page_size + 1;
  const end = Math.min(data.page * data.page_size, data.total);
  paginationInfo.textContent = `Showing ${start}–${end} of ${data.total}`;
  pageIndicator.textContent = `Page ${data.page} of ${data.total_pages}`;
  prevPageBtn.disabled = data.page <= 1;
  nextPageBtn.disabled = data.page >= data.total_pages;
}

async function doAction(action, licenseId) {
  const labels = {
    activate: "Activate this key?",
    deactivate: "Deactivate this key?",
    ban: "Ban this key? This will block all future verification requests.",
    "reset-device": "Reset the registered device for this key? The next successful verification will bind a new device.",
  };
  const ok = await confirmAction("Confirm action", labels[action] || "Are you sure?");
  if (!ok) return;

  try {
    await apiFetch(`/admin/api/keys/${action}`, {
      method: "POST",
      body: JSON.stringify({ license_id: licenseId }),
    });
    showToast("Done.");
    loadKeys();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function doExtend(licenseId) {
  const ok = await confirmAction("Extend expiry", "Extend this key's expiry by 7 days?");
  if (!ok) return;
  try {
    await apiFetch(`/admin/api/keys/extend`, {
      method: "POST",
      body: JSON.stringify({ license_id: licenseId, additional_days: 7 }),
    });
    showToast("Expiry extended.");
    loadKeys();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function doDelete(licenseId) {
  const ok = await confirmAction("Delete key", "Permanently delete this license key and its device/log history? This cannot be undone.");
  if (!ok) return;
  try {
    await apiFetch(`/admin/api/keys/${licenseId}`, { method: "DELETE" });
    showToast("Key deleted.");
    loadKeys();
  } catch (err) {
    showToast(err.message, "error");
  }
}

searchInput.addEventListener("input", debounce(() => { currentPage = 1; loadKeys(); }, 350));
statusFilter.addEventListener("change", () => { currentPage = 1; loadKeys(); });
prevPageBtn.addEventListener("click", () => { if (currentPage > 1) { currentPage--; loadKeys(); } });
nextPageBtn.addEventListener("click", () => { currentPage++; loadKeys(); });

loadKeys();
