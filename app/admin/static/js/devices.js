let currentPage = 1;
const pageSize = 20;

const searchInput = document.getElementById("searchInput");
const devicesBody = document.getElementById("devicesBody");
const paginationInfo = document.getElementById("paginationInfo");
const pageIndicator = document.getElementById("pageIndicator");
const prevPageBtn = document.getElementById("prevPageBtn");
const nextPageBtn = document.getElementById("nextPageBtn");

async function loadDevices() {
  devicesBody.innerHTML = `<tr class="loading-row"><td colspan="5"><div class="spinner" style="margin:0 auto;"></div></td></tr>`;

  const params = new URLSearchParams({ page: currentPage, page_size: pageSize });
  if (searchInput.value.trim()) params.set("search", searchInput.value.trim());

  try {
    const data = await apiFetch(`/admin/api/devices?${params.toString()}`);
    if (!data) return;

    if (data.items.length === 0) {
      devicesBody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><div class="empty-state-icon">▣</div>No registered devices</div></td></tr>`;
    } else {
      devicesBody.innerHTML = data.items.map((d) => `
        <tr>
          <td class="mono">${d.license_key || "—"}</td>
          <td class="mono">${d.installation_id}</td>
          <td class="text-secondary">${d.app_version || "—"}</td>
          <td class="text-muted">${formatDate(d.registered_at)}</td>
          <td class="text-muted">${formatDate(d.last_login)}</td>
        </tr>
      `).join("");
    }

    const start = data.total === 0 ? 0 : (data.page - 1) * data.page_size + 1;
    const end = Math.min(data.page * data.page_size, data.total);
    paginationInfo.textContent = `Showing ${start}–${end} of ${data.total}`;
    pageIndicator.textContent = `Page ${data.page} of ${data.total_pages}`;
    prevPageBtn.disabled = data.page <= 1;
    nextPageBtn.disabled = data.page >= data.total_pages;
  } catch (err) {
    devicesBody.innerHTML = `<tr><td colspan="5" class="empty-state">Failed to load devices</td></tr>`;
    showToast(err.message, "error");
  }
}

searchInput.addEventListener("input", debounce(() => { currentPage = 1; loadDevices(); }, 350));
prevPageBtn.addEventListener("click", () => { if (currentPage > 1) { currentPage--; loadDevices(); } });
nextPageBtn.addEventListener("click", () => { currentPage++; loadDevices(); });

loadDevices();
