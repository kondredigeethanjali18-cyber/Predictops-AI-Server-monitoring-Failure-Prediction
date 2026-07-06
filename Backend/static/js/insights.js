// PredictOps AI - Insights & ML Operations (RBAC Enforced)

let currentUserInfo = null;

function showInsightsToast(message, isError = false) {
    const toast = document.getElementById("insightsToast");
    if (!toast) return;
    toast.innerHTML = `<i class="fas fa-${isError ? 'triangle-exclamation' : 'circle-check'}" style="color: ${isError ? '#f87171' : '#4ade80'}; font-size: 16px;"></i> <span>${message}</span>`;
    toast.style.display = "flex";
    toast.style.background = isError ? "#7f1d1d" : "#0f172a";
    setTimeout(() => {
        toast.style.display = "none";
    }, 4000);
}

async function loadCurrentUserAuth() {
    try {
        const resp = await fetch("/api/auth/me");
        if (resp.ok) {
            currentUserInfo = await resp.json();
            updateMlRbacControls();
        }
    } catch (err) {
        console.debug("Error loading auth info in insights:", err);
    }
}

function updateMlRbacControls() {
    if (!currentUserInfo) return;
    const role = (currentUserInfo.role || "viewer").toLowerCase();
    const permissions = currentUserInfo.permissions || [];

    const badge = document.getElementById("mlCurrentRoleBadge");
    if (badge) {
        if (role === "admin") {
            badge.className = "role-badge role-admin";
            badge.innerHTML = `<i class="fas fa-shield-halved"></i> ADMIN`;
        } else if (role === "devops" || role === "engineer") {
            badge.className = "role-badge role-devops";
            badge.innerHTML = `<i class="fas fa-screwdriver-wrench"></i> DEVOPS ENGINEER`;
        } else {
            badge.className = "role-badge role-viewer";
            badge.innerHTML = `<i class="fas fa-eye"></i> VIEWER`;
        }
    }

    const btnDiag = document.getElementById("btnRunDiagnostics");
    const btnRetrain = document.getElementById("btnRetrainModel");
    const btnHotReload = document.getElementById("btnHotReloadModel");

    const canDiag = permissions.includes("ml.diagnostics") || role === "admin" || role === "devops" || role === "engineer";
    const canRetrain = permissions.includes("ml.retrain") || role === "admin";
    const canHotReload = permissions.includes("ml.hot_reload") || role === "admin";

    if (btnDiag) {
        if (!canDiag) {
            btnDiag.disabled = true;
            btnDiag.style.opacity = "0.5";
            btnDiag.style.cursor = "not-allowed";
            btnDiag.title = "You do not have permission to perform this action.";
        } else {
            btnDiag.disabled = false;
            btnDiag.style.opacity = "1";
            btnDiag.style.cursor = "pointer";
            btnDiag.title = "Execute ML inference diagnostics";
        }
    }

    if (btnRetrain) {
        if (!canRetrain) {
            btnRetrain.disabled = true;
            btnRetrain.style.opacity = "0.5";
            btnRetrain.style.cursor = "not-allowed";
            btnRetrain.title = "You do not have permission to perform this action. (Admin Only)";
        } else {
            btnRetrain.disabled = false;
            btnRetrain.style.opacity = "1";
            btnRetrain.style.cursor = "pointer";
            btnRetrain.title = "Retrain ML ensemble classifiers";
        }
    }

    if (btnHotReload) {
        if (!canHotReload) {
            btnHotReload.disabled = true;
            btnHotReload.style.opacity = "0.5";
            btnHotReload.style.cursor = "not-allowed";
            btnHotReload.title = "You do not have permission to perform this action. (Admin Only)";
        } else {
            btnHotReload.disabled = false;
            btnHotReload.style.opacity = "1";
            btnHotReload.style.cursor = "pointer";
            btnHotReload.title = "Hot-reload ML model artifact from disk";
        }
    }
}

async function loadInsights() {
    try {
        const response = await fetch("/ai-insights");
        if (!response.ok) return;
        const data = await response.json();

        // 1. Top Cards
        const topRiskEl = document.getElementById("topRisk");
        if (topRiskEl) {
            topRiskEl.innerHTML = `<i class="fas fa-server" style="color: #64748b; margin-right: 6px;"></i> ${data.top_risk || "None"}`;
        }

        const highestCpuEl = document.getElementById("highestCPU");
        if (highestCpuEl) {
            const cpuVal = data.highest_cpu_val !== undefined ? `${data.highest_cpu_val}%` : "";
            highestCpuEl.innerHTML = `<i class="fas fa-microchip" style="color: #64748b; margin-right: 6px;"></i> ${data.highest_cpu || "None"} <span style="font-size: 16px; color: #dc2626; font-weight: 700;">${cpuVal}</span>`;
        }

        const highestMemEl = document.getElementById("highestMemory");
        if (highestMemEl) {
            const memVal = data.highest_memory_val !== undefined ? `${data.highest_memory_val}%` : "";
            highestMemEl.innerHTML = `<i class="fas fa-memory" style="color: #64748b; margin-right: 6px;"></i> ${data.highest_memory || "None"} <span style="font-size: 16px; color: #8b5cf6; font-weight: 700;">${memVal}</span>`;
        }

        // Subtext and tags
        const topRiskSubtext = document.getElementById("topRiskSubtext");
        if (topRiskSubtext && data.top_risk_confidence) {
            topRiskSubtext.innerText = `Anomaly confidence: ${data.top_risk_confidence}%`;
        }

        const activeAnomaliesCountText = document.getElementById("activeAnomaliesCountText");
        if (activeAnomaliesCountText && data.total_anomalies !== undefined) {
            activeAnomaliesCountText.innerText = `${data.total_anomalies} Active Anomalies Detected`;
        }

        // 2. Risk and Confidence Gauges
        const riskScoreEl = document.getElementById("riskScore");
        if (riskScoreEl) {
            riskScoreEl.innerText = data.risk_score || "96%";
        }

        const riskScoreBar = document.getElementById("riskScoreBar");
        if (riskScoreBar) {
            const numRisk = parseFloat(data.risk_score) || 96;
            riskScoreBar.style.width = `${Math.min(100, numRisk)}%`;
        }

        const predConfEl = document.getElementById("predictionConfidence");
        if (predConfEl) {
            predConfEl.innerText = data.prediction_confidence || "95%";
        }

        const confScoreBar = document.getElementById("confidenceScoreBar");
        if (confScoreBar) {
            const numConf = parseFloat(data.prediction_confidence) || 95;
            confScoreBar.style.width = `${Math.min(100, numConf)}%`;
        }

        // 3. AI Recommendation
        const recEl = document.getElementById("recommendation");
        if (recEl && data.recommendation) {
            recEl.innerHTML = `<i class="fas fa-robot" style="color: #2563eb; margin-right: 6px;"></i> ${data.recommendation}`;
        }

        // Causes Pills
        const causesPillsEl = document.getElementById("causesPills");
        if (causesPillsEl) {
            if (data.top_risk_causes && data.top_risk_causes.length > 0) {
                causesPillsEl.innerHTML = data.top_risk_causes
                    .map(c => `<span class="badge-danger" style="margin-right: 4px; margin-bottom: 4px;"><i class="fas fa-triangle-exclamation"></i> ${c}</span>`)
                    .join("");
            } else {
                causesPillsEl.innerHTML = `<span class="badge-success"><i class="fas fa-circle-check"></i> Standard Telemetry Baseline</span>`;
            }
        }

        // 4. Suggested Actions Checklist
        const actionListEl = document.getElementById("actionList");
        if (actionListEl && data.actions && data.actions.length > 0) {
            actionListEl.innerHTML = data.actions
                .map(action => `
                    <li style="display: flex; align-items: flex-start; gap: 10px; font-size: 13px; color: #334155; line-height: 1.4;">
                        <i class="fas fa-circle-check" style="color: #2563eb; margin-top: 3px; font-size: 14px;"></i>
                        <span>${action}</span>
                    </li>
                `)
                .join("");
        }

    } catch (error) {
        console.error("Error loading insights:", error);
    }
}

// -------------------------------------------------------------------------
// ML Diagnostics Execution
// -------------------------------------------------------------------------
async function triggerDiagnostics() {
    const btn = document.getElementById("btnRunDiagnostics");
    const outCard = document.getElementById("diagnosticsOutputCard");
    const outText = document.getElementById("diagOutputText");
    const outTime = document.getElementById("diagExecutionTime");

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Running...';
    }

    try {
        const resp = await fetch("/api/ml/diagnostics", { method: "POST" });
        const data = await resp.json();

        if (!resp.ok || !data.success) {
            showInsightsToast(data.detail || "Diagnostics execution failed", true);
            return;
        }

        if (outCard && outText) {
            outCard.style.display = "block";
            outText.textContent = JSON.stringify(data.diagnostics, null, 2);
            if (outTime) outTime.textContent = new Date().toLocaleTimeString();
        }

        showInsightsToast("Inference diagnostics executed successfully.");

    } catch (err) {
        showInsightsToast(`Error: ${err.message}`, true);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-play"></i> Run Diagnostics';
        }
    }
}

// -------------------------------------------------------------------------
// ML Retraining Modals & Submission
// -------------------------------------------------------------------------
function openRetrainModal() {
    const modal = document.getElementById("retrainConfirmModal");
    if (modal) modal.style.display = "flex";
}

function closeRetrainModal() {
    const modal = document.getElementById("retrainConfirmModal");
    if (modal) modal.style.display = "none";
}

async function submitRetrain() {
    const btn = document.getElementById("btnConfirmRetrainSubmit");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Retraining...';
    }

    try {
        const resp = await fetch("/api/ml/retrain", { method: "POST" });
        const data = await resp.json();

        closeRetrainModal();

        if (!resp.ok || !data.success) {
            showInsightsToast(data.detail || "Retraining failed", true);
            return;
        }

        const outCard = document.getElementById("diagnosticsOutputCard");
        const outText = document.getElementById("diagOutputText");
        const outTime = document.getElementById("diagExecutionTime");

        if (outCard && outText) {
            outCard.style.display = "block";
            outText.textContent = JSON.stringify(data.result, null, 2);
            if (outTime) outTime.textContent = new Date().toLocaleTimeString();
        }

        showInsightsToast(data.result?.message || "Model retrained and saved successfully.");
        loadInsights();

    } catch (err) {
        showInsightsToast(`Retrain error: ${err.message}`, true);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-play"></i> Confirm Retrain';
        }
    }
}

// -------------------------------------------------------------------------
// ML Hot-Reload Modals & Submission
// -------------------------------------------------------------------------
function openHotReloadModal() {
    const modal = document.getElementById("hotReloadConfirmModal");
    if (modal) modal.style.display = "flex";
}

function closeHotReloadModal() {
    const modal = document.getElementById("hotReloadConfirmModal");
    if (modal) modal.style.display = "none";
}

async function submitHotReload() {
    const btn = document.getElementById("btnConfirmHotReloadSubmit");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Reloading...';
    }

    try {
        const resp = await fetch("/api/ml/hot-reload", { method: "POST" });
        const data = await resp.json();

        closeHotReloadModal();

        if (!resp.ok || !data.success) {
            showInsightsToast(data.detail || "Hot reload failed", true);
            return;
        }

        const outCard = document.getElementById("diagnosticsOutputCard");
        const outText = document.getElementById("diagOutputText");
        const outTime = document.getElementById("diagExecutionTime");

        if (outCard && outText) {
            outCard.style.display = "block";
            outText.textContent = JSON.stringify(data.result, null, 2);
            if (outTime) outTime.textContent = new Date().toLocaleTimeString();
        }

        showInsightsToast(data.result?.message || "Model hot-reloaded successfully.");

    } catch (err) {
        showInsightsToast(`Hot-reload error: ${err.message}`, true);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-arrows-rotate"></i> Hot-Reload';
        }
    }
}

function initInsights() {
    loadCurrentUserAuth();
    loadInsights();
    setInterval(loadInsights, 10000);
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initInsights);
} else {
    initInsights();
}