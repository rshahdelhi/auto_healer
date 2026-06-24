const samples = {
  dynatrace: {
    projectId: "checkout",
    projectName: "Checkout",
    component: "payments-api",
    severity: "critical",
    message: "p95 latency crossed threshold",
  },
  splunk: {
    projectId: "inventory",
    projectName: "Inventory",
    component: "stock-api",
    severity: "warning",
    message: "Error rate increased above baseline",
  },
  splunk_system: {
    projectId: "platform",
    projectName: "Platform",
    component: "node-17",
    severity: "critical",
    message: "Root filesystem usage reached 96%",
  },
  splunk_application: {
    projectId: "checkout",
    projectName: "Checkout",
    component: "payments-api",
    severity: "critical",
    message: "Payment authorization exceptions crossed threshold",
  },
  phoenix: {
    projectId: "customer-care",
    projectName: "Customer Care",
    component: "case-worker",
    severity: "info",
    message: "Queue depth returned to normal",
  },
  generic: {
    projectId: "platform",
    projectName: "Platform",
    component: "gateway",
    severity: "critical",
    message: "Synthetic check failed",
  },
  adfs: {
    projectId: "identity",
    projectName: "Identity Platform",
    component: "adfs",
    severity: "critical",
    message: "ADFS sign-in failures surged above 20% for five minutes",
  },
  capacity_up: {
    projectId: "checkout",
    projectName: "Checkout",
    component: "web-frontend",
    severity: "warning",
    message: "CPU utilization reached 86% and request queue depth is growing",
  },
  capacity_down: {
    projectId: "analytics",
    projectName: "Analytics",
    component: "batch-worker",
    severity: "info",
    message: "CPU utilization stayed below 15% for thirty minutes",
  },
  off_hours: {
    projectId: "backoffice",
    projectName: "Back Office",
    component: "reporting-service",
    severity: "info",
    message: "Application is eligible to stop during configured off hours",
  },
};

const form = document.querySelector("#eventForm");
const source = document.querySelector("#source");
const projectId = document.querySelector("#projectId");
const projectName = document.querySelector("#projectName");
const component = document.querySelector("#component");
const severity = document.querySelector("#severity");
const message = document.querySelector("#message");
const payloadPreview = document.querySelector("#payloadPreview");
const submitStatus = document.querySelector("#submitStatus");
const eventsTable = document.querySelector("#eventsTable");
const metrics = document.querySelector("#metrics");
const healthStatus = document.querySelector("#healthStatus");
const projectFilter = document.querySelector("#projectFilter");
const componentFilter = document.querySelector("#componentFilter");
const policyForm = document.querySelector("#policyForm");
const policyProjectId = document.querySelector("#policyProjectId");
const policyProjectName = document.querySelector("#policyProjectName");
const policyComponent = document.querySelector("#policyComponent");
const minReplicas = document.querySelector("#minReplicas");
const maxReplicas = document.querySelector("#maxReplicas");
const scaleUpThreshold = document.querySelector("#scaleUpThreshold");
const scaleDownThreshold = document.querySelector("#scaleDownThreshold");
const stopDuringOffHours = document.querySelector("#stopDuringOffHours");
const offHoursStart = document.querySelector("#offHoursStart");
const offHoursEnd = document.querySelector("#offHoursEnd");
const stopDuringHolidays = document.querySelector("#stopDuringHolidays");
const holidayCalendar = document.querySelector("#holidayCalendar");
const policyStatus = document.querySelector("#policyStatus");
const policiesList = document.querySelector("#policiesList");
const auditList = document.querySelector("#auditList");
const postmortemForm = document.querySelector("#postmortemForm");
const incidentId = document.querySelector("#incidentId");
const postmortemStatus = document.querySelector("#postmortemStatus");
const postmortemProjectId = document.querySelector("#postmortemProjectId");
const postmortemProjectName = document.querySelector("#postmortemProjectName");
const postmortemComponent = document.querySelector("#postmortemComponent");
const postmortemSeverity = document.querySelector("#postmortemSeverity");
const postmortemOwner = document.querySelector("#postmortemOwner");
const postmortemTitle = document.querySelector("#postmortemTitle");
const postmortemSummary = document.querySelector("#postmortemSummary");
const postmortemImpact = document.querySelector("#postmortemImpact");
const postmortemRootCause = document.querySelector("#postmortemRootCause");
const postmortemActions = document.querySelector("#postmortemActions");
const postmortemLessons = document.querySelector("#postmortemLessons");
const postmortemStatusText = document.querySelector("#postmortemStatusText");
const postmortemsList = document.querySelector("#postmortemsList");

function buildPayload() {
  const base = {
    component: component.value.trim(),
    severity: severity.value,
    message: message.value.trim(),
  };

  if (source.value === "dynatrace") {
    return {
      ...base,
      projectId: projectId.value.trim(),
      projectName: projectName.value.trim(),
      source: "dynatrace",
      event_name: "Dynatrace problem notification",
      dt_problem_id: `P-${Date.now()}`,
      impacted_entities: [component.value.trim()],
    };
  }

  if (source.value === "splunk") {
    return {
      ...base,
      project_id: projectId.value.trim(),
      project_name: projectName.value.trim(),
      monitoring_system: "splunk",
      search_name: "Auto Healer Mock Alert",
      sid: `splunk-${Date.now()}`,
    };
  }

  if (source.value === "splunk_system") {
    return {
      search_name: "System Error Surge",
      sid: `splunk-system-${Date.now()}`,
      app: "platform",
      owner: "auto-healer",
      alert_type: "system_error",
      result: {
        project_id: projectId.value.trim(),
        project_name: projectName.value.trim(),
        component: component.value.trim(),
        host: component.value.trim(),
        severity: severity.value,
        message: message.value.trim(),
        error: "disk_usage_high",
        filesystem: "/",
        usage_percent: 96,
      },
    };
  }

  if (source.value === "splunk_application") {
    return {
      search_name: "Application Error Surge",
      sid: `splunk-app-${Date.now()}`,
      app: "checkout",
      owner: "auto-healer",
      alert_type: "application_error",
      result: {
        project_id: projectId.value.trim(),
        project_name: projectName.value.trim(),
        component: component.value.trim(),
        severity: severity.value,
        message: message.value.trim(),
        exception: "PaymentAuthorizationException",
        error_count: 148,
        error_rate_percent: 18,
      },
    };
  }

  if (source.value === "phoenix") {
    return {
      ...base,
      pid: projectId.value.trim(),
      project: projectName.value.trim(),
      source: "phoenix",
      incident_key: `phoenix-${Date.now()}`,
      runbook: "auto-healer-demo",
    };
  }

  if (source.value === "adfs") {
    return {
      ...base,
      project_id: projectId.value.trim(),
      project_name: projectName.value.trim(),
      source: "adfs",
      event_name: "ADFS authentication error surge",
      error_rate_percent: 23,
      failed_logins: 1840,
      recommendation: "scale_up_identity_tier",
      action: "scale_up",
    };
  }

  if (source.value === "capacity_up") {
    return {
      ...base,
      project_id: projectId.value.trim(),
      project_name: projectName.value.trim(),
      source: "capacity-controller",
      event_name: "Scale up candidate",
      cpu_percent: 86,
      queue_depth: 142,
      recommendation: "scale_up",
      action: "scale_up",
    };
  }

  if (source.value === "capacity_down") {
    return {
      ...base,
      project_id: projectId.value.trim(),
      project_name: projectName.value.trim(),
      source: "capacity-controller",
      event_name: "Scale down candidate",
      cpu_percent: 14,
      queue_depth: 2,
      recommendation: "scale_down",
      action: "scale_down",
    };
  }

  if (source.value === "off_hours") {
    return {
      ...base,
      project_id: projectId.value.trim(),
      project_name: projectName.value.trim(),
      source: "schedule-controller",
      event_name: "Stop window candidate",
      recommendation: "stop_application",
      action: "stop",
      window_type: "off_hours",
    };
  }

  return {
    ...base,
    project_id: projectId.value.trim(),
    project_name: projectName.value.trim(),
    source: "generic",
    external_id: `generic-${Date.now()}`,
  };
}

function renderPayload() {
  payloadPreview.textContent = JSON.stringify(buildPayload(), null, 2);
}

function applySample() {
  const sample = samples[source.value];
  projectId.value = sample.projectId;
  projectName.value = sample.projectName;
  component.value = sample.component;
  severity.value = sample.severity;
  message.value = sample.message;
  syncPolicyIdentity();
  renderPayload();
}

function syncPolicyIdentity() {
  policyProjectId.value = projectId.value;
  policyProjectName.value = projectName.value;
  policyComponent.value = component.value;
  postmortemProjectId.value = projectId.value;
  postmortemProjectName.value = projectName.value;
  postmortemComponent.value = component.value;
}

async function checkHealth() {
  try {
    const response = await fetch("/health");
    if (!response.ok) {
      throw new Error("service unavailable");
    }
    healthStatus.textContent = "Service online";
    healthStatus.classList.add("ok");
  } catch {
    healthStatus.textContent = "Service offline";
    healthStatus.classList.remove("ok");
  }
}

async function sendEvent(event) {
  event.preventDefault();
  submitStatus.textContent = "Sending...";

  const endpoint = source.value.startsWith("splunk") ? "/splunk/alerts" : "/events";
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildPayload()),
  });

  if (!response.ok) {
    const body = await response.json();
    submitStatus.textContent = body.error || "Failed to send event";
    return;
  }

  submitStatus.textContent = "Event saved";
  syncPolicyIdentity();
  await loadEvents();
}

async function savePolicy(event) {
  event.preventDefault();
  policyStatus.textContent = "Saving...";

  const payload = {
    project_id: policyProjectId.value.trim(),
    project_name: policyProjectName.value.trim(),
    component: policyComponent.value.trim(),
    min_replicas: Number(minReplicas.value),
    max_replicas: Number(maxReplicas.value),
    scale_up_threshold: Number(scaleUpThreshold.value),
    scale_down_threshold: Number(scaleDownThreshold.value),
    stop_during_off_hours: stopDuringOffHours.checked,
    off_hours_start: offHoursStart.value,
    off_hours_end: offHoursEnd.value,
    stop_during_holidays: stopDuringHolidays.checked,
    holiday_calendar: holidayCalendar.value.trim(),
  };

  const response = await fetch("/policies", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const body = await response.json();
    policyStatus.textContent = body.error || "Failed to save policy";
    return;
  }

  policyStatus.textContent = "Policy saved";
  await loadPolicies();
  await loadAudit();
}

async function savePostmortem(event) {
  event.preventDefault();
  postmortemStatusText.textContent = "Saving...";

  const payload = {
    incident_id: incidentId.value.trim(),
    project_id: postmortemProjectId.value.trim(),
    project_name: postmortemProjectName.value.trim(),
    component: postmortemComponent.value.trim(),
    title: postmortemTitle.value.trim(),
    severity: postmortemSeverity.value,
    status: postmortemStatus.value,
    owner: postmortemOwner.value.trim(),
    summary: postmortemSummary.value.trim(),
    impact: postmortemImpact.value.trim(),
    root_cause: postmortemRootCause.value.trim(),
    corrective_actions: postmortemActions.value.trim(),
    lessons_learned: postmortemLessons.value.trim(),
  };

  const response = await fetch("/postmortems", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const body = await response.json();
    postmortemStatusText.textContent = body.error || "Failed to save postmortem";
    return;
  }

  postmortemStatusText.textContent = "Postmortem saved";
  await loadPostmortems();
  await loadAudit();
}

async function loadEvents() {
  const params = new URLSearchParams({ limit: "100" });
  if (projectFilter.value.trim()) {
    params.set("project_id", projectFilter.value.trim());
  }
  if (componentFilter.value.trim()) {
    params.set("component", componentFilter.value.trim());
  }

  const response = await fetch(`/events?${params.toString()}`);
  const body = await response.json();
  renderMetrics(body.events);
  renderEvents(body.events);
}

async function loadPolicies() {
  const response = await fetch("/policies?limit=50");
  const body = await response.json();
  renderPolicies(body.policies);
}

async function loadAudit() {
  const response = await fetch("/audit-log?limit=25");
  const body = await response.json();
  renderAudit(body.audit_log);
}

async function loadPostmortems() {
  const response = await fetch("/postmortems?limit=25");
  const body = await response.json();
  renderPostmortems(body.postmortems);
}

function renderMetrics(events) {
  const sources = new Set(events.map((event) => event.source));
  const critical = events.filter((event) => event.severity === "critical").length;
  const projects = new Set(events.map((event) => event.project_id || event.project_name));

  metrics.innerHTML = [
    ["Events", events.length],
    ["Critical", critical],
    ["Projects", projects.size],
    ["Sources", sources.size],
  ]
    .map(
      ([label, value]) => `
        <div class="metric-card">
          <span class="metric-label">${label}</span>
          <span class="metric-value">${value}</span>
        </div>
      `,
    )
    .join("");
}

function renderEvents(events) {
  if (events.length === 0) {
    eventsTable.innerHTML = `
      <tr>
        <td colspan="6">No events stored yet.</td>
      </tr>
    `;
    return;
  }

  eventsTable.innerHTML = events
    .map(
      (event) => `
        <tr>
          <td>${formatTime(event.created_at)}</td>
          <td>${escapeHtml(event.project_id || event.project_name || "unknown")}</td>
          <td>${escapeHtml(event.component)}</td>
          <td>${escapeHtml(event.source)}</td>
          <td><span class="badge ${escapeHtml(event.severity || "info")}">${escapeHtml(event.severity || "info")}</span></td>
          <td>${escapeHtml(event.message || event.title || "")}</td>
        </tr>
      `,
    )
    .join("");
}

function renderPolicies(policies) {
  if (policies.length === 0) {
    policiesList.innerHTML = `<p class="policy-chip">No policies saved yet.</p>`;
    return;
  }

  policiesList.innerHTML = policies
    .map(
      (policy) => `
        <article class="policy-item">
          <div class="policy-title">
            <strong>${escapeHtml(policy.project_id || policy.project_name || "unknown")} / ${escapeHtml(policy.component)}</strong>
            <span class="badge info">${escapeHtml(policy.min_replicas)}-${escapeHtml(policy.max_replicas)} replicas</span>
          </div>
          <div class="policy-grid">
            <span class="policy-chip">Scale up at ${escapeHtml(policy.scale_up_threshold)}%</span>
            <span class="policy-chip">Scale down at ${escapeHtml(policy.scale_down_threshold)}%</span>
            <span class="policy-chip">Off hours: ${policy.stop_during_off_hours ? `${escapeHtml(policy.off_hours_start || "")}-${escapeHtml(policy.off_hours_end || "")}` : "disabled"}</span>
            <span class="policy-chip">Holidays: ${policy.stop_during_holidays ? "stop enabled" : "disabled"}</span>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderAudit(entries) {
  if (entries.length === 0) {
    auditList.innerHTML = `<p class="policy-chip">No rule or configuration changes recorded yet.</p>`;
    return;
  }

  auditList.innerHTML = entries
    .map(
      (entry) => `
        <article class="audit-item">
          <div class="audit-title">
            <strong>${escapeHtml(entry.summary)}</strong>
            <span class="badge info">${escapeHtml(entry.action)}</span>
          </div>
          <div class="audit-meta">
            ${escapeHtml(entry.entity_type)} · ${escapeHtml(entry.entity_id)} · ${formatTime(entry.created_at)}
          </div>
        </article>
      `,
    )
    .join("");
}

function renderPostmortems(postmortems) {
  if (postmortems.length === 0) {
    postmortemsList.innerHTML = `<p class="policy-chip">No postmortems saved yet.</p>`;
    return;
  }

  postmortemsList.innerHTML = postmortems
    .map(
      (postmortem) => `
        <article class="policy-item">
          <div class="policy-title">
            <strong>${escapeHtml(postmortem.incident_id)} · ${escapeHtml(postmortem.title)}</strong>
            <span class="badge info">${escapeHtml(postmortem.status.replace("_", " "))}</span>
          </div>
          <div class="policy-grid">
            <span class="policy-chip">Project: ${escapeHtml(postmortem.project_id || postmortem.project_name || "unknown")}</span>
            <span class="policy-chip">Component: ${escapeHtml(postmortem.component)}</span>
            <span class="policy-chip">Severity: ${escapeHtml(postmortem.severity || "unknown")}</span>
            <span class="policy-chip">Owner: ${escapeHtml(postmortem.owner || "unassigned")}</span>
          </div>
          <p class="audit-meta">${escapeHtml(postmortem.summary || "No summary yet.")}</p>
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

source.addEventListener("change", applySample);
projectId.addEventListener("input", syncPolicyIdentity);
projectName.addEventListener("input", syncPolicyIdentity);
component.addEventListener("input", syncPolicyIdentity);
form.addEventListener("input", renderPayload);
form.addEventListener("submit", sendEvent);
policyForm.addEventListener("submit", savePolicy);
postmortemForm.addEventListener("submit", savePostmortem);
document.querySelector("#randomizeButton").addEventListener("click", applySample);
document.querySelector("#refreshButton").addEventListener("click", loadEvents);
document.querySelector("#policyRefreshButton").addEventListener("click", loadPolicies);
document.querySelector("#auditRefreshButton").addEventListener("click", loadAudit);
document.querySelector("#postmortemRefreshButton").addEventListener("click", loadPostmortems);

applySample();
checkHealth();
loadEvents();
loadPolicies();
loadAudit();
loadPostmortems();
