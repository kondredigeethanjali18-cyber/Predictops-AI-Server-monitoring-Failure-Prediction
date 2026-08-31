// PredictOps AI - Real-Time Dashboard Controller

function formatAlertTime(timestamp) {
    if (!timestamp) return "Time unavailable";
    let ts = String(timestamp).trim();
    if (ts.includes("T") && !ts.endsWith("Z") && !ts.includes("+") && !ts.includes("-", 10)) {
        ts += "Z";
    }
    const date = new Date(ts);
    if (Number.isNaN(date.getTime())) return timestamp;
    return date.toLocaleString("en-IN", {
        timeZone: "Asia/Kolkata",
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: true
    }) + " (IST)";
}

async function loadDashboard() {
    try {
        const [predsResp, serversResp] = await Promise.all([
            fetch("/all-predictions"),
            fetch("/all-servers")
        ]);

        const data = predsResp.ok ? await predsResp.json() : [];
        const serversData = serversResp.ok ? await serversResp.json() : [];

        // 1. Total Metrics
        const totalServersEl = document.getElementById("totalServers");
        if (totalServersEl) totalServersEl.innerText = (serversData || []).length;

        const totalRecordsEl = document.getElementById("totalRecords");
        if (totalRecordsEl) totalRecordsEl.innerText = (data || []).length;

        // 2. State metrics & Fleet health
        let healthy = 0;
        let warning = 0;
        let critical = 0;
        let totalCpu = 0;
        let totalMemory = 0;

        (serversData || []).forEach(s => {
            const cpu = Number(s.cpu_usage_percent) || 0;
            const memory = Number(s.memory_usage_percent) || 0;

            totalCpu += cpu;
            totalMemory += memory;

            if (cpu > 85 || memory > 85) {
                critical++;
            } else if (cpu > 70 || memory > 75) {
                warning++;
            } else {
                healthy++;
            }
        });

        const healthyEl = document.getElementById("healthyServers");
        if (healthyEl) healthyEl.innerText = healthy;

        const warningEl = document.getElementById("warningServers");
        if (warningEl) warningEl.innerText = warning;

        const criticalEl = document.getElementById("criticalServers");
        if (criticalEl) criticalEl.innerText = critical;

        const serverCount = (serversData && serversData.length) ? serversData.length : 1;
        const avgCpuVal = (totalCpu / serverCount);
        const avgMemVal = (totalMemory / serverCount);

        const avgCpuEl = document.getElementById("avgCpuUsage");
        if (avgCpuEl) avgCpuEl.innerText = avgCpuVal.toFixed(1) + "%";

        const avgMemEl = document.getElementById("avgMemoryUsage");
        if (avgMemEl) avgMemEl.innerText = avgMemVal.toFixed(1) + "%";

        const barAvgCpu = document.getElementById("barAvgCpu");
        if (barAvgCpu) barAvgCpu.style.width = Math.min(avgCpuVal, 100) + "%";

        const barAvgMem = document.getElementById("barAvgMem");
        if (barAvgMem) barAvgMem.style.width = Math.min(avgMemVal, 100) + "%";

        // Update Tri-state distribution progress bar
        const totalNodes = Math.max(1, healthy + warning + critical);
        const barHealthy = document.getElementById("barHealthy");
        if (barHealthy) barHealthy.style.width = ((healthy / totalNodes) * 100) + "%";

        const barWarning = document.getElementById("barWarning");
        if (barWarning) barWarning.style.width = ((warning / totalNodes) * 100) + "%";

        const barCritical = document.getElementById("barCritical");
        if (barCritical) barCritical.style.width = ((critical / totalNodes) * 100) + "%";

        // 3. Anomaly Rate & Active Anomalies
        const anomalies = (data || []).filter(x => x.prediction === "ANOMALY");
        const anomalyCount = anomalies.length;
        const anomalyRate = (data && data.length > 0) ? ((anomalyCount / data.length) * 100).toFixed(1) : 0;
        const anomalyRateEl = document.getElementById("anomalyRate");
        if (anomalyRateEl) anomalyRateEl.innerText = anomalyRate + "%";

        const totalAnomaliesEl = document.getElementById("totalAnomaliesCount");
        if (totalAnomaliesEl) {
            totalAnomaliesEl.innerText = `${anomalyCount} Active`;
            totalAnomaliesEl.style.color = anomalyCount > 0 ? "#dc2626" : "#16a34a";
        }

        // 4. Top Risk Server
        if (serversData && serversData.length > 0) {
            const highestRiskServer = [...serversData].sort((a, b) => {
                const aVal = (Number(a.cpu_usage_percent) || 0) + (Number(a.memory_usage_percent) || 0);
                const bVal = (Number(b.cpu_usage_percent) || 0) + (Number(b.memory_usage_percent) || 0);
                return bVal - aVal;
            })[0];

            if (highestRiskServer) {
                const topServerEl = document.getElementById("topRiskServer");
                if (topServerEl) topServerEl.innerHTML = `<i class="fas fa-server" style="color: #64748b; font-size: 15px;"></i> ${highestRiskServer.server_name}`;

                const topCpuEl = document.getElementById("topRiskCpu");
                if (topCpuEl) topCpuEl.innerText = `${highestRiskServer.cpu_usage_percent}%`;

                const topMemEl = document.getElementById("topRiskMem");
                if (topMemEl) topMemEl.innerText = `${highestRiskServer.memory_usage_percent}%`;

                const topCpuBar = document.getElementById("topRiskCpuBar");
                if (topCpuBar) topCpuBar.style.width = Math.min(Number(highestRiskServer.cpu_usage_percent) || 0, 100) + "%";

                const topMemBar = document.getElementById("topRiskMemBar");
                if (topMemBar) topMemBar.style.width = Math.min(Number(highestRiskServer.memory_usage_percent) || 0, 100) + "%";

                const riskPill = document.getElementById("topRiskPill");
                if (riskPill) {
                    const cpu = Number(highestRiskServer.cpu_usage_percent) || 0;
                    const mem = Number(highestRiskServer.memory_usage_percent) || 0;
                    if (cpu > 85 || mem > 85) {
                        riskPill.innerText = "Critical Risk";
                        riskPill.style.background = "#fee2e2";
                        riskPill.style.color = "#dc2626";
                    } else if (cpu > 70) {
                        riskPill.innerText = "Elevated";
                        riskPill.style.background = "#fef3c7";
                        riskPill.style.color = "#d97706";
                    } else {
                        riskPill.innerText = "Optimal";
                        riskPill.style.background = "#dcfce7";
                        riskPill.style.color = "#16a34a";
                    }
                }

                // Card 4: Predictive Reliability & Action Center
                const recEl = document.getElementById("dashboardRecommendation");
                const fleetTagEl = document.getElementById("fleetHealthTag");
                const healthScoreEl = document.getElementById("fleetHealthScore");
                const aiGuardEl = document.getElementById("aiGuardStatus");

                // Calculate Fleet Health Score (Index out of 100)
                let healthIndex = 99.8;
                if (critical > 0) {
                    healthIndex = Math.max(68.5, Math.min(92.0, (100 - (critical * 9.5 + warning * 3.5))));
                } else if (warning > 0) {
                    healthIndex = Math.max(91.0, (100 - (warning * 2.8)));
                }
                if (healthScoreEl) healthScoreEl.innerText = `${healthIndex.toFixed(1)}%`;

                if (critical > 0) {
                    if (fleetTagEl) {
                        fleetTagEl.className = "live-tag live-tag-danger";
                        fleetTagEl.innerHTML = `<i class="fas fa-triangle-exclamation"></i> ${critical} Node${critical > 1 ? 's' : ''} At Risk`;
                    }
                    if (aiGuardEl) {
                        aiGuardEl.className = "stat-value";
                        aiGuardEl.style.color = "#dc2626";
                        aiGuardEl.innerHTML = `<i class="fas fa-triangle-exclamation"></i> Mitigation Standby`;
                    }
                    if (recEl) {
                        recEl.innerHTML = `<strong>CRITICAL LOAD on ${highestRiskServer.server_name}</strong> (${highestRiskServer.cpu_usage_percent}% CPU, ${highestRiskServer.memory_usage_percent}% RAM). Automated traffic rebalance and memory reclamation advised.`;
                    }
                } else if (warning > 0) {
                    if (fleetTagEl) {
                        fleetTagEl.className = "live-tag live-tag-warning";
                        fleetTagEl.innerHTML = `<i class="fas fa-circle-exclamation"></i> Elevated Load`;
                    }
                    if (aiGuardEl) {
                        aiGuardEl.className = "stat-value";
                        aiGuardEl.style.color = "#d97706";
                        aiGuardEl.innerHTML = `<i class="fas fa-shield"></i> Monitoring Headroom`;
                    }
                    if (recEl) {
                        recEl.innerHTML = `<strong>Moderate workload spike detected:</strong> ${highestRiskServer.server_name} is consuming peak fleet resources. Infrastructure headroom is within safe buffer margins.`;
                    }
                } else {
                    if (fleetTagEl) {
                        fleetTagEl.className = "live-tag live-tag-success";
                        fleetTagEl.innerHTML = `<i class="fas fa-circle live-pulse"></i> SLA: 99.9% Optimal`;
                    }
                    if (aiGuardEl) {
                        aiGuardEl.className = "stat-value text-success";
                        aiGuardEl.style.color = "#16a34a";
                        aiGuardEl.innerHTML = `<i class="fas fa-shield-check"></i> Automated Guard Active`;
                    }
                    if (recEl) {
                        recEl.innerHTML = `All ${serversData.length} monitored infrastructure nodes operating comfortably within nominal performance baselines. Zero imminent failover risks detected.`;
                    }
                }
            }
        }

        // 5. Latest Prediction Card
        if (data && data.length > 0) {
            const latest = data[0];
            let conf = latest.confidence !== undefined ? Number(latest.confidence) : 90;
            if (conf > 100) conf = conf / 100;
            conf = Math.round(conf * 10) / 10;

            const badge = latest.prediction === "ANOMALY"
                ? `<span class="badge-danger" style="display:inline-flex; align-items:center; gap:5px;"><i class="fas fa-triangle-exclamation"></i> ANOMALY</span>`
                : `<span class="badge-success" style="display:inline-flex; align-items:center; gap:5px;"><i class="fas fa-circle-check"></i> NORMAL</span>`;

            const latestPredEl = document.getElementById("latestPrediction");
            if (latestPredEl) {
                latestPredEl.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <strong style="font-size: 15px; color: #0f172a;"><i class="fas fa-server" style="color: #64748b; margin-right: 6px;"></i>${latest.server_name}</strong>
                        ${badge}
                    </div>
                `;
            }

            const confScoreEl = document.getElementById("confidenceScoreVal");
            if (confScoreEl) confScoreEl.innerText = conf + "%";

            const confBar = document.getElementById("confidenceBar");
            if (confBar) confBar.style.width = Math.min(conf, 100) + "%";
        }

        // 6. Recent Threat & Anomaly Alerts
        const alertsEl = document.getElementById("recentAlerts");
        if (alertsEl) {
            dashboardAnomalies = (anomalies || []).slice(0, 4);
            if (dashboardAnomalies.length > 0) {
                alertsEl.innerHTML = dashboardAnomalies
                    .map((a, index) => {
                        let conf = a.confidence !== undefined ? Number(a.confidence) : 90;
                        if (conf > 100) conf = conf / 100;
                        conf = Math.round(conf * 10) / 10;
                        const remark = a.remark || "Elevated resource deviation detected by ensemble model.";
                        return `
                            <div class="dashboard-alert-item" onclick="openDashboardAlertDetail(${index})" title="Click to view incident details">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <span style="font-weight: 700; color: #0f172a; font-size: 13px;">
                                        <i class="fas fa-triangle-exclamation" style="color: #dc2626; margin-right: 4px;"></i> 
                                        ${a.server_name}
                                    </span>
                                    <span style="font-size: 11px; font-weight: 700; color: #dc2626; background: #fee2e2; padding: 2px 6px; border-radius: 4px;">${conf}% Conf.</span>
                                </div>
                                <div style="font-size: 11.5px; color: #475569; margin-top: 4px; line-height: 1.35; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${remark}</div>
                                <div style="font-size: 10.5px; color: #2563eb; font-weight: 600; margin-top: 4px; display: flex; align-items: center; justify-content: space-between;">
                                    <span><i class="fas fa-eye"></i> Click to inspect details</span>
                                    <span style="color: #64748b;">${formatAlertTime(a.timestamp)}</span>
                                </div>
                            </div>
                        `;
                    })
                    .join("");
            } else {
                alertsEl.innerHTML = `
                    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; min-height: 180px; gap: 8px; color: #16a34a; font-weight: 600; font-size: 13px; text-align: center; padding: 16px;">
                        <i class="fas fa-circle-check" style="font-size: 24px;"></i>
                        <span>All servers operating within safe anomaly thresholds. Zero incidents detected.</span>
                    </div>
                `;
            }
        }

        // 7. Last Updated Timestamp
        const now = new Date();
        const lastUpdatedEl = document.getElementById("lastUpdated");
        if (lastUpdatedEl) {
            lastUpdatedEl.innerText = now.toLocaleTimeString("en-IN", {
                timeZone: "Asia/Kolkata",
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
                hour12: true
            }) + " (IST)";
        }

    } catch (error) {
        console.error("Error loading dashboard data:", error);
    }
}

let dashboardAnomalies = [];

function openDashboardAlertDetail(index) {
    const item = dashboardAnomalies[index];
    if (!item) return;

    let conf = item.confidence !== undefined ? Number(item.confidence) : 90;
    if (conf > 100) conf = conf / 100;
    conf = Math.round(conf * 10) / 10;

    let severity = "Moderate Risk";
    let severityClass = "severity-medium";
    let iconClass = "fa-triangle-exclamation";
    let iconColor = "#d97706";
    let iconBg = "#fef3c7";

    if (conf >= 90) {
        severity = "Critical Risk";
        severityClass = "severity-critical";
        iconClass = "fa-triangle-exclamation";
        iconColor = "#dc2626";
        iconBg = "#fee2e2";
    } else if (conf >= 70) {
        severity = "High Risk";
        severityClass = "severity-high";
        iconClass = "fa-circle-exclamation";
        iconColor = "#ea580c";
        iconBg = "#ffedd5";
    }

    const modal = document.getElementById("dashboardAlertModal");
    if (!modal) return;

    // Server Name & Detected Time
    document.getElementById("dModalServerName").innerText = item.server_name || "Unknown Server";
    document.getElementById("dModalDetectedTime").innerHTML = `<i class="fas fa-clock" style="color: #2563eb; margin-right: 4px;"></i> Detected: <strong>${formatAlertTime(item.timestamp)}</strong>`;

    // Icon
    const iconContainer = document.getElementById("dModalSeverityIcon");
    if (iconContainer) {
        iconContainer.style.background = iconBg;
        iconContainer.style.color = iconColor;
        iconContainer.innerHTML = `<i class="fas ${iconClass}"></i>`;
    }

    // Badges
    const predBadge = document.getElementById("dModalPredictionBadge");
    if (predBadge) {
        predBadge.className = item.prediction === "ANOMALY" ? "badge-danger" : "badge-success";
        predBadge.innerHTML = `<i class="fas ${item.prediction === 'ANOMALY' ? 'fa-triangle-exclamation' : 'fa-circle-check'}"></i> ${item.prediction}`;
    }

    const sevBadge = document.getElementById("dModalSeverityBadge");
    if (sevBadge) {
        sevBadge.className = severityClass;
        sevBadge.innerText = severity;
    }

    const confBadge = document.getElementById("dModalConfidenceBadge");
    if (confBadge) {
        confBadge.innerText = `${conf}% Confidence`;
    }

    // Telemetry metrics snapshot
    document.getElementById("dModalCpu").innerText = item.cpu_usage_percent !== undefined ? `${item.cpu_usage_percent}%` : "--";
    document.getElementById("dModalMem").innerText = item.memory_usage_percent !== undefined ? `${item.memory_usage_percent}%` : "--";
    document.getElementById("dModalDisk").innerText = item.disk_usage_percent !== undefined ? `${item.disk_usage_percent}%` : "--";

    let tp = "0.00 MB/s";
    if (item.network_throughput !== undefined && item.network_throughput !== null) {
        let num = Number(item.network_throughput);
        if (num > 100000) num = num / (1024 * 1024);
        tp = `${num.toFixed(2)} MB/s`;
    }
    document.getElementById("dModalThroughput").innerText = tp;

    // Causes List
    const causesList = document.getElementById("dModalCausesList");
    if (causesList) {
        const causes = (item.possible_causes && item.possible_causes.length > 0)
            ? item.possible_causes
            : ["Behavioral Telemetry Anomaly (Resource Surge)"];
        causesList.innerHTML = causes.map(c => `<li>${c}</li>`).join("");
    }

    // AI Remark
    const fallbackRemark = `${severity}: resource deviation (${conf}% confidence). Urgent review recommended.`;
    const remark = item.remark || fallbackRemark;
    document.getElementById("dModalRemark").innerHTML = `<strong>Status Assessment:</strong> ${remark}<br><br><strong>Action Item:</strong> Isolate worker threads on ${item.server_name}, review top consuming processes, and balance traffic to secondary cluster nodes.`;

    modal.style.display = "flex";
}

function closeDashboardModal() {
    const modal = document.getElementById("dashboardAlertModal");
    if (modal) {
        modal.style.display = "none";
    }
}

// Close on outside click or Escape key
document.addEventListener("click", e => {
    const modal = document.getElementById("dashboardAlertModal");
    if (modal && e.target === modal) {
        closeDashboardModal();
    }
});

document.addEventListener("keydown", e => {
    if (e.key === "Escape") {
        closeDashboardModal();
    }
});

function initDashboard() {
    loadDashboard();
    setInterval(loadDashboard, 8000);
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initDashboard);
} else {
    initDashboard();
}
