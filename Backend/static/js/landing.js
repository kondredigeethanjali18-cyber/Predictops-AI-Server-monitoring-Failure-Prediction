async function loadStats() {
    try {
        const response = await fetch("/dashboard-summary");
        const data = await response.json();

        // 1. Update KPI Counters
        const serverCountEl = document.getElementById("serverCount");
        if (serverCountEl) {
            serverCountEl.innerText = data.total_records !== undefined ? data.total_records : (data.total || 0);
        }

        const alertCountEl = document.getElementById("alertCount");
        if (alertCountEl) {
            alertCountEl.innerText = data.active_alerts !== undefined ? data.active_alerts : ((data.critical || 0) + (data.warning || 0));
        }

        const accuracyEl = document.getElementById("accuracyCount");
        if (accuracyEl && data.prediction_accuracy) {
            accuracyEl.innerText = data.prediction_accuracy;
        }

        // 2. Update Live Fleet Health Preview
        const fleetHealthEl = document.getElementById("landingFleetHealth");
        if (fleetHealthEl && data.fleet_health_score) {
            fleetHealthEl.innerText = data.fleet_health_score;
        }

        // 3. Update Live Operations Server List
        const panelListEl = document.getElementById("landingPanelList");
        if (panelListEl && data.top_servers && data.top_servers.length > 0) {
            panelListEl.innerHTML = data.top_servers.map(s => {
                let icon = "fa-server";
                if (s.risk_class === "risk-high") icon = "fa-triangle-exclamation";
                else if (s.risk_class === "risk-medium") icon = "fa-memory";
                else icon = "fa-circle-check";

                return `
                    <div class="panel-row">
                        <span><i class="fas ${icon}"></i> ${s.server_name} <small style="color: #94a3b8; font-size: 11px; margin-left: 4px;">(${s.cpu}% CPU)</small></span>
                        <strong class="${s.risk_class}">${s.status}</strong>
                    </div>
                `;
            }).join("");
        }

        // 4. Update Footer note
        const footerEl = document.getElementById("landingAlertFooter");
        if (footerEl) {
            const now = new Date().toLocaleTimeString("en-IN", {
                timeZone: "Asia/Kolkata",
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
                hour12: true
            });
            footerEl.innerHTML = `<i class="fas fa-bolt" style="color: #2563eb;"></i> Live sync active at ${now} (IST) — ${data.total_servers || 26} nodes connected`;
        }

    } catch (error) {
        console.error("Error loading landing stats:", error);
    }
}

// Initial load & 8-second interval
loadStats();
setInterval(loadStats, 8000);