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

        // Top Risk and Latest Prediction
        if (data.length > 0) {
            const riskServer = data.reduce((max, current) => {
                const currentRisk = (current.cpu_usage_percent || 0) + (current.memory_usage_percent || 0);
                const maxRisk = (max.cpu_usage_percent || 0) + (max.memory_usage_percent || 0);
                return currentRisk > maxRisk ? current : max;
            });

            document.getElementById("topRiskServer").innerText = riskServer.server_name;

            const latest = data[0];
            const badgeClass = latest.prediction === "ANOMALY" ? "badge-danger" : "badge-success";
            document.getElementById("latestPrediction").innerHTML = 
                `<span class="${badgeClass}">${latest.prediction}</span> 
                 <span style="font-size: 13px; color: #64748b; margin-left: 5px;">(${latest.confidence}% confidence)</span>`;

            document.getElementById("lastUpdated").innerText = new Date().toLocaleTimeString();
        }

        // Recent Alerts
        const anomalies = data.filter(x => x.prediction === "ANOMALY");

        if (anomalies.length > 0) {
            document.getElementById("recentAlerts").innerHTML = anomalies
                .slice(0, 3)
                .map(a => {
                    const severity = a.confidence >= 90 ? "Critical" : (a.confidence >= 70 ? "High" : "Medium");
                    const fallbackRemark = `${severity}: resource usage deviation (${a.confidence}% confidence).`;
                    const remark = a.remark || fallbackRemark;
                    return `
                        <div style="margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px dashed #e2e8f0; text-align: left;">
                            <span class="alert-line" style="font-weight: 600; display: inline-flex; align-items: center; gap: 6px;">
                                <i class="fas fa-circle-exclamation alert-icon alert-icon-danger"></i> 
                                ${a.server_name} <span style="font-size: 12px; font-weight: normal; color: #dc2626;">(${a.confidence}% confidence)</span>
                            </span>
                            <div style="font-size: 12px; color: #64748b; margin-top: 4px; padding-left: 20px; line-height: 1.4;">${remark}</div>
                        </div>
                    `;
                })
                .join("");
        } else {
            document.getElementById("recentAlerts").innerHTML =
                '<span class="alert-line"><i class="fas fa-circle-check alert-icon alert-icon-success"></i> No active alerts</span>';
        }

    } catch (error) {
        console.error("Error loading dashboard data:", error);
    }
}

loadDashboard();
setInterval(loadDashboard, 3000);
