async function loadDashboard() {
    try {
        const response = await fetch("/all-predictions");
        const data = await response.json();

        let healthy = 0;
        let warning = 0;
        let critical = 0;
        let totalCpu = 0;
        let totalMemory = 0;
        let anomalyCount = 0;
        const serverNames = new Set();

        data.forEach(server => {
            serverNames.add(server.server_name || "Unknown");
            totalCpu += Number(server.cpu_usage_percent || 0);
            totalMemory += Number(server.memory_usage_percent || 0);
            if (server.prediction === "ANOMALY") {
                anomalyCount++;
            }

            const cpu = server.cpu_usage_percent;
            const memory = server.memory_usage_percent;

            if (cpu > 90 || memory > 90) {
                critical++;
            } else if (cpu > 70 || memory > 80) {
                warning++;
            } else {
                healthy++;
            }
        });

        // Set card metrics
        document.getElementById("totalServers").innerText = serverNames.size;
        document.getElementById("totalRecords").innerText = data.length;
        document.getElementById("healthyServers").innerText = healthy;
        document.getElementById("warningServers").innerText = warning;
        document.getElementById("criticalServers").innerText = critical;

        const avgCpu = data.length > 0 ? (totalCpu / data.length).toFixed(1) : 0;
        const avgMemory = data.length > 0 ? (totalMemory / data.length).toFixed(1) : 0;
        const anomalyRate = data.length > 0 ? ((anomalyCount / data.length) * 100).toFixed(1) : 0;

        document.getElementById("avgCpuUsage").innerText = `${avgCpu}%`;
        document.getElementById("avgMemoryUsage").innerText = `${avgMemory}%`;
        document.getElementById("anomalyRate").innerText = `${anomalyRate}%`;

        // Top Risk Server & Latest Prediction
        if (data.length > 0) {
            const riskServer = data.reduce((max, current) => {
                const currentRisk = (Number(current.cpu_usage_percent) || 0) + (Number(current.memory_usage_percent) || 0);
                const maxRisk = (Number(max.cpu_usage_percent) || 0) + (Number(max.memory_usage_percent) || 0);
                return currentRisk > maxRisk ? current : max;
            });

            const topRiskEl = document.getElementById("topRiskServer");
            if (topRiskEl) topRiskEl.innerText = riskServer.server_name || "Unknown";

            const cpuVal = Number(riskServer.cpu_usage_percent) || 0;
            const memVal = Number(riskServer.memory_usage_percent) || 0;
            const totalRiskScore = cpuVal + memVal;

            const topRiskCpuEl = document.getElementById("topRiskCpu");
            if (topRiskCpuEl) topRiskCpuEl.innerText = `${cpuVal}%`;

            const topRiskMemEl = document.getElementById("topRiskMem");
            if (topRiskMemEl) topRiskMemEl.innerText = `${memVal}%`;

            const topRiskCpuBar = document.getElementById("topRiskCpuBar");
            if (topRiskCpuBar) topRiskCpuBar.style.width = `${Math.min(cpuVal, 100)}%`;

            const topRiskMemBar = document.getElementById("topRiskMemBar");
            if (topRiskMemBar) topRiskMemBar.style.width = `${Math.min(memVal, 100)}%`;

            const topRiskPill = document.getElementById("topRiskPill");
            if (topRiskPill) {
                if (totalRiskScore > 160 || cpuVal > 85 || memVal > 85) {
                    topRiskPill.innerText = "Critical Risk";
                    topRiskPill.className = "risk-pill";
                    topRiskPill.style.background = "#fee2e2";
                    topRiskPill.style.color = "#991b1b";
                } else if (totalRiskScore > 120) {
                    topRiskPill.innerText = "Elevated";
                    topRiskPill.className = "risk-pill";
                    topRiskPill.style.background = "#fef3c7";
                    topRiskPill.style.color = "#92400e";
                } else {
                    topRiskPill.innerText = "Moderate";
                    topRiskPill.className = "risk-pill";
                    topRiskPill.style.background = "#dcfce7";
                    topRiskPill.style.color = "#166534";
                }
            }

            // Latest Prediction
            const latest = data[0];
            const badgeClass = latest.prediction === "ANOMALY" ? "badge-danger" : "badge-success";
            const latestPredEl = document.getElementById("latestPrediction");
            if (latestPredEl) {
                latestPredEl.innerHTML = `
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                        <strong style="color: #0f172a; font-size: 16px;">${latest.server_name}</strong>
                        <span class="${badgeClass}">${latest.prediction}</span>
                    </div>
                    <div style="font-size: 12px; color: #64748b; line-height: 1.4;">${latest.remark || 'Operating within expected baseline parameters.'}</div>
                `;
            }

            const confScore = latest.confidence !== undefined ? latest.confidence : 100;
            const confValEl = document.getElementById("confidenceScoreVal");
            if (confValEl) confValEl.innerText = `${confScore}%`;

            const confBar = document.getElementById("confidenceBar");
            if (confBar) confBar.style.width = `${Math.min(confScore, 100)}%`;

            // Last Updated
            const lastUpEl = document.getElementById("lastUpdated");
            if (lastUpEl) {
                lastUpEl.innerText = new Date().toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour12: true }) + " (IST)";
            }
        }

        // Recent Alerts
        const anomalies = data.filter(x => x.prediction === "ANOMALY");
        const alertsEl = document.getElementById("recentAlerts");

        if (alertsEl) {
            if (anomalies.length > 0) {
                alertsEl.innerHTML = anomalies
                    .slice(0, 2)
                    .map(a => {
                        const severity = a.confidence >= 90 ? "Critical" : (a.confidence >= 70 ? "High" : "Medium");
                        const fallbackRemark = `${severity}: resource usage deviation (${a.confidence}% confidence).`;
                        const remark = a.remark || fallbackRemark;
                        return `
                            <div style="margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px dashed #e2e8f0; text-align: left;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <span style="font-weight: 700; color: #0f172a; font-size: 13px;">
                                        <i class="fas fa-triangle-exclamation" style="color: #dc2626; margin-right: 4px;"></i> 
                                        ${a.server_name}
                                    </span>
                                    <span style="font-size: 11px; font-weight: 700; color: #dc2626; background: #fee2e2; padding: 2px 6px; border-radius: 4px;">${a.confidence}%</span>
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

    } catch (error) {
        console.error("Error loading dashboard data:", error);
    }
}

loadDashboard();
setInterval(loadDashboard, 3000);
