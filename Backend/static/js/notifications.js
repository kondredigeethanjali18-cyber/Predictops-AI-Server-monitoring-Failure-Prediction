// PredictOps AI - Global Notification Bell & Real-Time Incident Alerts

const APP_TIME_SHIFT_MS = (5 * 60 + 29) * 60 * 1000;

function formatNotificationTime(timestamp) {
    if (!timestamp) return "Time unavailable";
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return timestamp;

    const shiftedDate = new Date(date.getTime() + APP_TIME_SHIFT_MS);
    return shiftedDate.toLocaleString("en-IN", {
        timeZone: "Asia/Kolkata",
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: true
    }) + " (IST)";
}

async function loadNotifications() {
    const countEl = document.getElementById("notificationCount");
    const panelEl = document.getElementById("notificationPanel");
    const listEl = document.getElementById("notificationList") || panelEl;

    if (!countEl || !panelEl) return;

    try {
        const response = await fetch("/all-server-predictions");
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const predictions = await response.json();
        const anomalies = (predictions || []).filter(item => item.prediction === "ANOMALY");

        countEl.innerText = anomalies.length;
        if (anomalies.length > 0) {
            countEl.classList.remove("empty");
        } else {
            countEl.classList.add("empty");
        }

        if (anomalies.length === 0) {
            listEl.innerHTML = `
                <div class="notification-empty">
                    <i class="fas fa-circle-check"></i>
                    <div><strong>All Systems Optimal</strong></div>
                    <span style="font-size: 11.5px; color: #64748b;">No active anomaly alerts detected</span>
                </div>
            `;
            return;
        }

        const html = anomalies.slice(0, 10).map(item => {
            let conf = item.confidence !== undefined ? Number(item.confidence) : 90;
            if (conf > 100) conf = conf / 100;
            conf = Math.round(conf * 10) / 10;

            const timeStr = formatNotificationTime(item.timestamp);
            const causeText = (item.possible_causes && item.possible_causes.length > 0)
                ? item.possible_causes[0]
                : "Resource Stress Detected";

            return `
                <div class="notification-item">
                    <i class="fas fa-triangle-exclamation alert-icon"></i>
                    <div class="notification-item-content">
                        <div style="display: flex; justify-content: space-between; align-items: baseline;">
                            <strong>${item.server_name}</strong>
                            <span style="color: #ef4444; font-weight: 700; font-size: 11.5px;">${conf}% Conf.</span>
                        </div>
                        <div style="font-size: 12px; color: #94a3b8; margin-top: 2px;">${causeText}</div>
                        <div class="notification-time">
                            <i class="fas fa-clock" style="color: #3b82f6;"></i> ${timeStr}
                        </div>
                    </div>
                </div>
            `;
        }).join("");

        listEl.innerHTML = html;

    } catch (error) {
        console.error("Notification load error:", error);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const bell = document.getElementById("notificationBell");
    const panel = document.getElementById("notificationPanel");

    if (bell && panel) {
        bell.addEventListener("click", (e) => {
            e.stopPropagation();
            panel.classList.toggle("active");
            if (panel.classList.contains("active")) {
                loadNotifications();
            }
        });

        document.addEventListener("click", (e) => {
            if (!e.target.closest(".notification-widget")) {
                panel.classList.remove("active");
            }
        });

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") {
                panel.classList.remove("active");
            }
        });

        loadNotifications();
        setInterval(loadNotifications, 8000);
    }
});
