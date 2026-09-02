function formatAlertTime(timestamp) {
    if (!timestamp) return "Time unavailable";
    const date = new Date(timestamp);
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
        const response = await fetch("/all-predictions");
        const data = await response.json();

        const serversResponse = await fetch("/all-servers");
        const serversData = await serversResponse.json();

        // 1. Total Metrics
        document.getElementById("totalServers").innerText = serversData.length;
        document.getElementById("totalRecords").innerText = data.length;

        // 2. State metrics & Fleet health
        let healthy = 0;
        let warning = 0;
        let critical = 0;
        let totalCpu = 0;
        let totalMemory = 0;

        serversData.forEach(s => {
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

        document.getElementById("healthyServers").innerText = healthy;
        document.getElementById("warningServers").innerText = warning;
        document.getElementById("criticalServers").innerText = critical;

        const serverCount = serversData.length || 1;
        document.getElementById("avgCpuUsage").innerText = (totalCpu / serverCount).toFixed(1) + "%";
        document.getElementById("avgMemoryUsage").innerText = (totalMemory / serverCount).toFixed(1) + "%";

        // 3. Anomaly Rate
        const anomalies = data.filter(x => x.prediction === "ANOMALY");
        const anomalyCount = anomalies.length;
        const anomalyRate = data.length > 0 ? ((anomalyCount / data.length) * 100).toFixed(1) : 0;
        document.getElementById("anomalyRate").innerText = anomalyRate + "%";

        // 4. Top Risk Server
        if (serversData.length > 0) {
            const highestRiskServer = [...serversData].sort(
                (a, b) => (b.cpu_usage_percent + b.memory_usage_percent) - (a.cpu_usage_percent + a.memory_usage_percent)
            )[0];

            document.getElementById("topRiskServer").innerHTML = `<i class="fas fa-server" style="color: #64748b; font-size: 15px;"></i> ${highestRiskServer.server_name}`;
            document.getElementById("topRiskCpu").innerText = highestRiskServer.cpu_usage_percent + "%";
            document.getElementById("topRiskMem").innerText = highestRiskServer.memory_usage_percent + "%";

            document.getElementById("topRiskCpuBar").style.width = Math.min(highestRiskServer.cpu_usage_percent, 100) + "%";
            document.getElementById("topRiskMemBar").style.width = Math.min(highestRiskServer.memory_usage_percent, 100) + "%";

            const riskPill = document.getElementById("topRiskPill");
            if (highestRiskServer.cpu_usage_percent > 85 || highestRiskServer.memory_usage_percent > 85) {
                riskPill.innerText = "Critical Risk";
                riskPill.style.background = "#fee2e2";
                riskPill.style.color = "#dc2626";
            } else if (highestRiskServer.cpu_usage_percent > 70) {
                riskPill.innerText = "Elevated";
                riskPill.style.background = "#fef3c7";
                riskPill.style.color = "#d97706";
            } else {
                riskPill.innerText = "Optimal";
                riskPill.style.background = "#dcfce7";
                riskPill.style.color = "#16a34a";
            }

            // Update Card 4: AI Remediation & Insights
            const recEl = document.getElementById("dashboardRecommendation");
            const actionEl = document.getElementById("dashboardSuggestedAction");
            const fleetTagEl = document.getElementById("fleetHealthTag");

            if (critical > 0) {
                if (fleetTagEl) fleetTagEl.innerHTML = `<i class="fas fa-triangle-exclamation" style="color: #dc2626;"></i> ${critical} High Stress Nodes`;
                if (recEl) recEl.innerText = `${highestRiskServer.server_name} is operating at critical capacity (${highestRiskServer.cpu_usage_percent}% CPU, ${highestRiskServer.memory_usage_percent}% MEM).`;
                if (actionEl) actionEl.innerHTML = `<i class="fas fa-wrench" style="color: #2563eb; margin-right: 6px;"></i> <strong>Recommended Action:</strong> Rebalance traffic from ${highestRiskServer.server_name} and check top process memory leaks.`;
            } else if (warning > 0) {
                if (fleetTagEl) fleetTagEl.innerHTML = `<i class="fas fa-circle-exclamation" style="color: #d97706;"></i> Moderate Load`;
                if (recEl) recEl.innerText = `Fleet load is moderately elevated. ${highestRiskServer.server_name} is currently the highest consumer.`;
                if (actionEl) actionEl.innerHTML = `<i class="fas fa-shield" style="color: #2563eb; margin-right: 6px;"></i> <strong>Recommended Action:</strong> Monitor compute headroom. Automated mitigation on standby.`;
            } else {
                if (fleetTagEl) fleetTagEl.innerHTML = `<i class="fas fa-circle live-pulse" style="color: #22c55e;"></i> All Stable`;
                if (recEl) recEl.innerText = `All ${serversData.length} monitored servers are operating comfortably within baseline.`;
                if (actionEl) actionEl.innerHTML = `<i class="fas fa-circle-check" style="color: #16a34a; margin-right: 6px;"></i> <strong>Status:</strong> Zero immediate interventions required. ML guard active.`;
            }
        }

        // 5. Latest Prediction Card
        if (data.length > 0) {
            const latest = data[0];
            let conf = latest.confidence !== undefined ? Number(latest.confidence) : 90;
            if (conf > 100) conf = conf / 100;
            conf = Math.round(conf * 10) / 10;

            const badge = latest.prediction === "ANOMALY"
                ? `<span class="badge-danger" style="display:inline-flex; align-items:center; gap:5px;"><i class="fas fa-triangle-exclamation"></i> ANOMALY</span>`
                : `<span class="badge-success" style="display:inline-flex; align-items:center; gap:5px;"><i class="fas fa-circle-check"></i> NORMAL</span>`;

            document.getElementById("latestPrediction").innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <strong style="font-size: 15px; color: #0f172a;"><i class="fas fa-server" style="color: #64748b; margin-right: 6px;"></i>${latest.server_name}</strong>
                    ${badge}
                </div>
            `;

            document.getElementById("confidenceScoreVal").innerText = conf + "%";
            document.getElementById("confidenceBar").style.width = Math.min(conf, 100) + "%";
        }

        // 6. Recent Threat & Anomaly Alerts
        const alertsEl = document.getElementById("recentAlerts");
        if (alertsEl) {
            const recentAnomalies = anomalies.slice(0, 3);
            if (recentAnomalies.length > 0) {
                alertsEl.innerHTML = recentAnomalies
                    .map(a => {
                        let conf = a.confidence !== undefined ? Number(a.confidence) : 90;
                        if (conf > 100) conf = conf / 100;
                        conf = Math.round(conf * 10) / 10;
                        const remark = a.remark || "Elevated resource deviation detected by ensemble model.";
                        return `
                            <div style="margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px dashed #e2e8f0; text-align: left;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <span style="font-weight: 700; color: #0f172a; font-size: 13px;">
                                        <i class="fas fa-triangle-exclamation" style="color: #dc2626; margin-right: 4px;"></i> 
                                        ${a.server_name}
                                    </span>
                                    <span style="font-size: 11px; font-weight: 700; color: #dc2626; background: #fee2e2; padding: 2px 6px; border-radius: 4px;">${conf}%</span>
                                </div>
                                <div style="font-size: 11px; color: #64748b; margin-top: 3px; line-height: 1.3;">${remark}</div>
                            </div>
                        `;
                    })
                    .join("");
            } else {
                alertsEl.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 8px; color: #16a34a; font-weight: 600; font-size: 13px; padding: 8px 0;">
                        <i class="fas fa-circle-check" style="font-size: 18px;"></i>
                        <span>All servers operating within safe anomaly thresholds.</span>
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

// Initial load & 8-second interval
loadDashboard();
setInterval(loadDashboard, 8000);
