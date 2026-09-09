// PredictOps AI - Landing Page Live Stats & Synchronized Countdown Controller

const REFRESH_INTERVAL_SECONDS = 8;
let remainingSeconds = REFRESH_INTERVAL_SECONDS;
let countdownTimer = null;
let lastSyncDate = new Date();
let isFetchingStats = false;

async function loadStats() {
    if (isFetchingStats) return;
    isFetchingStats = true;

    try {
        const response = await fetch("/dashboard-summary");
        if (!response.ok) {
            isFetchingStats = false;
            return;
        }
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

        // 2. Update Dynamic Fleet Health Score & Dynamic Ring Chart
        const fleetHealthEl = document.getElementById("landingFleetHealth");
        const healthRingEl = document.getElementById("landingHealthRing");
        const ringIconEl = document.querySelector("#landingHealthRingInner i");

        const scoreNum = data.health_score_num !== undefined 
            ? Number(data.health_score_num) 
            : (data.fleet_health_score ? parseFloat(data.fleet_health_score) : 100);

        const scoreColor = scoreNum >= 90 ? "#16a34a" : scoreNum >= 75 ? "#d97706" : "#dc2626";

        if (fleetHealthEl) {
            fleetHealthEl.innerText = data.fleet_health_score || `${scoreNum.toFixed(1)}%`;
            fleetHealthEl.style.color = scoreColor;
        }

        if (ringIconEl) {
            ringIconEl.style.color = scoreColor;
        }

        if (healthRingEl) {
            const hPct = data.healthy_pct !== undefined ? Number(data.healthy_pct) : 100;
            const wPct = data.warning_pct !== undefined ? Number(data.warning_pct) : 0;
            const cPct = data.critical_pct !== undefined ? Number(data.critical_pct) : 0;

            const stop1 = Math.max(0, Math.min(100, hPct));
            const stop2 = Math.max(stop1, Math.min(100, stop1 + wPct));

            // Dynamic conic gradient reflecting live proportions of Healthy (Green), Warning (Amber), Critical (Red)
            healthRingEl.style.background = `conic-gradient(#22c55e 0% ${stop1}%, #f59e0b ${stop1}% ${stop2}%, #ef4444 ${stop2}% 100%)`;
            healthRingEl.style.boxShadow = `0 4px 14px ${scoreNum >= 90 ? 'rgba(34, 197, 94, 0.25)' : scoreNum >= 75 ? 'rgba(245, 158, 11, 0.25)' : 'rgba(239, 68, 68, 0.25)'}`;
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

        // 5. Update Accurate Synced Time & Reset Countdown
        lastSyncDate = new Date();
        remainingSeconds = REFRESH_INTERVAL_SECONDS;
        renderSyncTimer();

    } catch (error) {
        console.error("Error loading landing stats:", error);
    } finally {
        isFetchingStats = false;
    }
}

function renderSyncTimer() {
    const syncTimeEl = document.getElementById("landingSyncTime");
    const remainingEl = document.getElementById("landingRemainingSecs");

    if (syncTimeEl) {
        syncTimeEl.innerText = lastSyncDate.toLocaleTimeString("en-IN", {
            timeZone: "Asia/Kolkata",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: true
        }) + " (IST)";
    }

    if (remainingEl) {
        remainingEl.innerText = `${remainingSeconds}s`;
    }
}

function startSyncCountdown() {
    if (countdownTimer) clearInterval(countdownTimer);

    countdownTimer = setInterval(() => {
        remainingSeconds--;
        const remainingEl = document.getElementById("landingRemainingSecs");
        const badgeEl = document.getElementById("landingCountdownBadge");

        if (remainingSeconds <= 0) {
            if (badgeEl) {
                badgeEl.innerHTML = `<i class="fas fa-spinner fa-spin" style="font-size: 10px;"></i> Syncing...`;
            }
            loadStats();
        } else {
            if (badgeEl) {
                badgeEl.innerHTML = `<i class="fas fa-rotate" style="font-size: 10px;"></i> Next in <strong id="landingRemainingSecs">${remainingSeconds}s</strong>`;
            }
        }
    }, 1000);
}

// Initial load & start synchronized countdown loop
loadStats();
startSyncCountdown();