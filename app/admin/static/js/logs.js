let currentPage = 1;
const pageSize = 30;

const statusFilter = document.getElementById("statusFilter");
const logsBody = document.getElementById("logsBody");
const paginationInfo = document.getElementById("paginationInfo");
const pageIndicator = document.getElementById("pageIndicator");
const prevPageBtn = document.getElementById("prevPageBtn");
const nextPageBtn = document.getElementById("nextPageBtn");

async function loadLogs() {
  logsBody.innerHTML = `<tr class="loading-row"><td colspan="5"><div class="spinner" style="margin:0 auto;"></div></td></tr>`;

  const params = new URLSearchParams({ page: currentPage, page_size: pageSize });
  if (statusFilter.value !== "ALL") params.set("status", statusFilter.value);

  try {
    const data = await apiFetch(`/admin/api/logs?${params.toString()}`);
    if (!data) return;

    if (data.items.length === 0) {
      logsBody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><div class="empty-state-icon">≡</div>No log entries</div></td></tr>`;
    } else {
      logsBody.innerHTML = data.items.map((l) => `
        <tr>
          <td>${statusBadge(l.status)}</td>
          <td class="mono">${l.license_key || "—"}</td>
          <td class="mono">${l.installation_id || "—"}</td>
          <td class="text-secondary">${l.source_ip || "—"}</td>
          <td class="text-muted">${formatDate(l.created_at)}</td>
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
    logsBody.innerHTML = `<tr><td colspan="5" class="empty-state">Failed to load logs</td></tr>`;
    showToast(err.message, "error");
  }
}

statusFilter.addEventListener("change", () => { currentPage = 1; loadLogs(); });
prevPageBtn.addEventListener("click", () => { if (currentPage > 1) { currentPage--; loadLogs(); } });
nextPageBtn.addEventListener("click", () => { currentPage++; loadLogs(); });

loadLogs();
