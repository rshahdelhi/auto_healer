const configForm = document.querySelector("#configForm");
const endpointUrl = document.querySelector("#endpointUrl");
const authType = document.querySelector("#authType");
const adfsClientId = document.querySelector("#adfsClientId");
const adfsServerId = document.querySelector("#adfsServerId");
const adfsUsername = document.querySelector("#adfsUsername");
const adfsPassword = document.querySelector("#adfsPassword");
const retryEnabled = document.querySelector("#retryEnabled");
const maxRetryAttempts = document.querySelector("#maxRetryAttempts");
const retryBackoffSeconds = document.querySelector("#retryBackoffSeconds");
const circuitBreakerEnabled = document.querySelector("#circuitBreakerEnabled");
const circuitBreakerFailureThreshold = document.querySelector("#circuitBreakerFailureThreshold");
const circuitBreakerResetTimeoutSeconds = document.querySelector("#circuitBreakerResetTimeoutSeconds");
const configStatus = document.querySelector("#configStatus");
const configSummary = document.querySelector("#configSummary");
const configAuditList = document.querySelector("#configAuditList");

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
  retryEnabled.checked = body.config.retry_enabled;
  maxRetryAttempts.value = body.config.max_retry_attempts;
  retryBackoffSeconds.value = body.config.retry_backoff_seconds;
  circuitBreakerEnabled.checked = body.config.circuit_breaker_enabled;
  circuitBreakerFailureThreshold.value = body.config.circuit_breaker_failure_threshold;
  circuitBreakerResetTimeoutSeconds.value = body.config.circuit_breaker_reset_timeout_seconds;
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
    retry_enabled: retryEnabled.checked,
    max_retry_attempts: Number(maxRetryAttempts.value),
    retry_backoff_seconds: Number(retryBackoffSeconds.value),
    circuit_breaker_enabled: circuitBreakerEnabled.checked,
    circuit_breaker_failure_threshold: Number(circuitBreakerFailureThreshold.value),
    circuit_breaker_reset_timeout_seconds: Number(circuitBreakerResetTimeoutSeconds.value),
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
  await loadConfigAudit();
}

async function loadConfigAudit() {
  const response = await fetch("/audit-log?entity_type=endpoint_config&limit=10");
  const body = await response.json();
  renderConfigAudit(body.audit_log);
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
        <span class="policy-chip">Retries: ${config.retry_enabled ? `${escapeHtml(config.max_retry_attempts)} attempts` : "disabled"}</span>
        <span class="policy-chip">Backoff: ${escapeHtml(config.retry_backoff_seconds)}s</span>
        <span class="policy-chip">Circuit breaker: ${config.circuit_breaker_enabled ? "enabled" : "disabled"}</span>
        <span class="policy-chip">Breaker threshold: ${escapeHtml(config.circuit_breaker_failure_threshold)}</span>
        <span class="policy-chip">Breaker reset: ${escapeHtml(config.circuit_breaker_reset_timeout_seconds)}s</span>
      </div>
    </div>
  `;
}

function renderConfigAudit(entries) {
  if (entries.length === 0) {
    configAuditList.innerHTML = `<p class="policy-chip">No configuration changes recorded yet.</p>`;
    return;
  }

  configAuditList.innerHTML = entries
    .map(
      (entry) => `
        <article class="audit-item">
          <div class="audit-title">
            <strong>${escapeHtml(entry.summary)}</strong>
            <span class="badge info">${escapeHtml(entry.action)}</span>
          </div>
          <div class="audit-meta">${formatTime(entry.created_at)}</div>
        </article>
      `,
    )
    .join("");
}

function formatTime(value) {
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    month: "short",
    day: "numeric",
  }).format(new Date(value));
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
document.querySelector("#configAuditRefreshButton").addEventListener("click", loadConfigAudit);
loadConfig();
loadConfigAudit();
