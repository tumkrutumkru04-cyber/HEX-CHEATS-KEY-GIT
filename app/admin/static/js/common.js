// ---------- Mobile sidebar ----------
(function () {
  const btn = document.getElementById("mobileMenuBtn");
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebarOverlay");
  if (!btn || !sidebar || !overlay) return;

  function close() {
    sidebar.classList.remove("open");
    overlay.classList.remove("open");
  }
  btn.addEventListener("click", () => {
    sidebar.classList.toggle("open");
    overlay.classList.toggle("open");
  });
  overlay.addEventListener("click", close);
})();

// ---------- Toasts ----------
function showToast(message, type = "success") {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transition = "opacity .2s ease";
    setTimeout(() => el.remove(), 200);
  }, 3200);
}

// ---------- Confirm modal ----------
function confirmAction(title, body) {
  return new Promise((resolve) => {
    const modal = document.getElementById("confirmModal");
    const titleEl = document.getElementById("confirmModalTitle");
    const bodyEl = document.getElementById("confirmModalBody");
    const cancelBtn = document.getElementById("confirmModalCancel");
    const confirmBtn = document.getElementById("confirmModalConfirm");
    if (!modal) { resolve(window.confirm(body || title)); return; }

    titleEl.textContent = title;
    bodyEl.textContent = body || "";
    modal.classList.add("open");

    function cleanup(result) {
      modal.classList.remove("open");
      cancelBtn.removeEventListener("click", onCancel);
      confirmBtn.removeEventListener("click", onConfirm);
      resolve(result);
    }
    function onCancel() { cleanup(false); }
    function onConfirm() { cleanup(true); }

    cancelBtn.addEventListener("click", onCancel);
    confirmBtn.addEventListener("click", onConfirm);
  });
}

// ---------- Fetch helper ----------
async function apiFetch(url, options = {}) {
  const opts = Object.assign({ headers: { "Content-Type": "application/json" } }, options);
  const res = await fetch(url, opts);
  if (res.status === 303) {
    window.location.href = "/admin/login";
    return null;
  }
  let data = null;
  try { data = await res.json(); } catch (e) { /* no body */ }
  if (!res.ok) {
    const message = (data && data.detail) || `Request failed (${res.status})`;
    throw new Error(message);
  }
  return data;
}

// ---------- Formatting helpers ----------
function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString(undefined, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function statusBadge(status) {
  if (!status) return "";
  const cls = "badge-" + status.toLowerCase();
  return `<span class="badge ${cls}">${status.replace(/_/g, " ")}</span>`;
}

function debounce(fn, wait) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
}
