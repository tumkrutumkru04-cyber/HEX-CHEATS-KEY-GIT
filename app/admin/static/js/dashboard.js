async function loadStats() {
  try {
    const data = await apiFetch("/admin/api/stats");
    if (!data) return;

    document.getElementById("stat-total").textContent = data.total_keys;
    document.getElementById("stat-active").textContent = data.active_keys;
    document.getElementById("stat-expired").textContent = data.expired_keys;
    document.getElementById("stat-banned").textContent = data.banned_keys;
    document.getElementById("stat-devices").textContent = data.registered_devices;

    document.querySelectorAll(".stat-value").forEach((el) => el.classList.remove("skeleton"));

    const body = document.getElementById("recentRequestsBody");
    if (!data.recent_requests || data.recent_requests.length === 0) {
      body.innerHTML = `<tr><td colspan="5" class="empty-state">No API requests yet</td></tr>`;
      return;
    }

    body.innerHTML = data.recent_requests.map((log) => `
      <tr>
        <td>${statusBadge(log.status)}</td>
        <td class="mono">${log.license_id ? log.license_id.slice(0, 8) + "…" : "—"}</td>
        <td class="mono">${log.installation_id || "—"}</td>
        <td class="text-secondary">${log.source_ip || "—"}</td>
        <td class="text-muted">${formatDate(log.created_at)}</td>
      </tr>
    `).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

loadStats();
