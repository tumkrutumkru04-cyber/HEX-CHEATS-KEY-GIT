document.getElementById("passwordForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("savePasswordBtn");
  btn.disabled = true;

  const current_password = document.getElementById("currentPassword").value;
  const new_password = document.getElementById("newPassword").value;

  try {
    await apiFetch("/admin/api/settings/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password, new_password }),
    });
    showToast("Password updated.");
    document.getElementById("passwordForm").reset();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
  }
});
