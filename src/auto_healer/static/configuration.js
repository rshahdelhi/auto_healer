const configForm = document.querySelector("#configForm");
const endpointUrl = document.querySelector("#endpointUrl");
const authType = document.querySelector("#authType");
const adfsClientId = document.querySelector("#adfsClientId");
const adfsServerId = document.querySelector("#adfsServerId");
const adfsUsername = document.querySelector("#adfsUsername");
const adfsPassword = document.querySelector("#adfsPassword");
const configStatus = document.querySelector("#configStatus");
const configSummary = document.querySelector("#configSummary");

async function loadConfig() {
  const response = await fetch("/endpoint-config");
  const body = await response.json();
  renderConfig(body.config);

  if (!body.config) {
    return;
  }

  endpointUrl.value = body.config.endpoint_url;
  authType.value = body.config.auth_type;
  adfsClientId.value = body.config.adfs_client_id;
  adfsServerId.value = body.config.adfs_server_id;
  adfsUsername.value = body.config.adfs_username;
  adfsPassword.placeholder = body.config.password_set ? "Saved password unchanged" : "";
}

async function saveConfig(event) {
  event.preventDefault();
  configStatus.textContent = "Saving...";

  const payload = {
    endpoint_url: endpointUrl.value.trim(),
    auth_type: authType.value,
    adfs_client_id: adfsClientId.value.trim(),
    adfs_server_id: adfsServerId.value.trim(),
    adfs_username: adfsUsername.value.trim(),
  };

  if (adfsPassword.value.trim()) {
    payload.adfs_password = adfsPassword.value;
  }

  const response = await fetch("/endpoint-config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const body = await response.json();
  if (!response.ok) {
    configStatus.textContent = body.error || "Failed to save configuration";
    return;
  }

  adfsPassword.value = "";
  adfsPassword.placeholder = "Saved password unchanged";
  configStatus.textContent = "Configuration saved";
  renderConfig(body);
}

function renderConfig(config) {
  if (!config) {
    configSummary.innerHTML = `<p class="policy-chip">No endpoint configuration saved yet.</p>`;
    return;
  }

  configSummary.innerHTML = `
    <div class="policy-item">
      <div class="policy-title">
        <strong>${escapeHtml(config.endpoint_url)}</strong>
        <span class="badge info">${escapeHtml(config.auth_type)}</span>
      </div>
      <div class="policy-grid">
        <span class="policy-chip">Client ID: ${escapeHtml(config.adfs_client_id)}</span>
        <span class="policy-chip">Server ID: ${escapeHtml(config.adfs_server_id)}</span>
        <span class="policy-chip">User: ${escapeHtml(config.adfs_username)}</span>
        <span class="policy-chip">Password: ${config.password_set ? "saved" : "missing"}</span>
      </div>
    </div>
  `;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

configForm.addEventListener("submit", saveConfig);
loadConfig();
