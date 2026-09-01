let alerts = [];
let filteredAlerts = [];
let activeSeverityFilter = "ALL";
let currentPage = 1;
const recordsPerPage = 10;

async function loadAlerts() {
    try {
        const response = await fetch("/all-server-predictions");
        const predictions = await response.json();

        alerts = predictions
            .filter(item => item.prediction === "ANOMALY")
            .sort((a, b) => {
                const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
                const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
                return timeB - timeA || b.confidence - a.confidence;
            });

        updateSummaryKpis();
        applyFilters();
        renderTable();
        renderNotification();

        const syncEl = document.getElementById("alertsSyncTime");
        if (syncEl) {
            syncEl.innerText = new Date().toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour12: true }) + " IST";
        }
    } catch(error) {
        console.error("Error loading alerts:", error);
    }
}

function updateSummaryKpis() {
    let critical = 0;
    let high = 0;
    let medium = 0;

    alerts.forEach(item => {
        const conf = Number(item.confidence) || 0;
        if (conf >= 90) {
            critical++;
        } else if (conf >= 70) {
            high++;
        } else {
            medium++;
        }
    });

    const totalEl = document.getElementById("totalActiveAlertsCount");
    if (totalEl) totalEl.innerText = alerts.length;

    const critEl = document.getElementById("criticalAlertsCount");
    if (critEl) critEl.innerText = critical;

    const highEl = document.getElementById("highAlertsCount");
    if (highEl) highEl.innerText = high;

    const medEl = document.getElementById("mediumAlertsCount");
    if (medEl) medEl.innerText = medium;
}

function applyFilters() {
    const searchInput = document.getElementById("searchAlertBox");
    const query = searchInput ? searchInput.value.trim().toLowerCase() : "";

    filteredAlerts = alerts.filter(item => {
        const matchesSearch = !query || 
            (item.server_name && item.server_name.toLowerCase().includes(query)) ||
            (item.remark && item.remark.toLowerCase().includes(query)) ||
            ((item.possible_causes || []).join(" ").toLowerCase().includes(query));

        let matchesSeverity = true;
        const conf = Number(item.confidence) || 0;
        let severity = "Medium";
        if (conf >= 90) severity = "Critical";
        else if (conf >= 70) severity = "High";

        if (activeSeverityFilter !== "ALL") {
            matchesSeverity = (severity === activeSeverityFilter);
        }

        return matchesSearch && matchesSeverity;
    });
}

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
    }) + " IST";
}

function renderTable() {
    const totalPages = Math.max(1, Math.ceil(filteredAlerts.length / recordsPerPage));

    if (currentPage > totalPages) {
        currentPage = totalPages;
    }

    const start = (currentPage - 1) * recordsPerPage;
    const end = start + recordsPerPage;
    const pageData = filteredAlerts.slice(start, end);

    if (pageData.length === 0) {
        document.getElementById("alertsTableBody").innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; color: #16a34a; font-weight: 600; padding: 28px;">
                    <i class="fas fa-circle-check" style="font-size: 24px; display: block; margin-bottom: 8px;"></i>
                    No matching anomaly alerts found. All systems operating within baseline parameters.
                </td>
            </tr>
        `;
        document.getElementById("alertPageNumber").innerText = "Page 1 of 1";
        document.getElementById("nextAlertBtn").disabled = true;
        document.getElementById("prevAlertBtn").disabled = true;
        return;
    }

    const html = pageData.map(item => {
        let severity = "Medium";
        let severityClass = "severity-medium";
        const conf = Number(item.confidence) || 0;

        if (conf >= 90) {
            severity = "Critical";
            severityClass = "severity-critical";
        } else if (conf >= 70) {
            severity = "High";
            severityClass = "severity-high";
        }

        const fallbackRemark = `${severity}: resource usage deviation (${conf}% confidence). Review recommended.`;
        const remark = item.remark || fallbackRemark;
        const formattedTime = formatAlertTime(item.timestamp);
        const causes = (item.possible_causes && item.possible_causes.length > 0)
            ? item.possible_causes.join(", ")
            : "No major issue detected";

        return `
            <tr>
                <td><strong style="color: #0f172a;"><i class="fas fa-server" style="color: #64748b; margin-right: 6px;"></i>${item.server_name}</strong></td>
                <td><span class="badge-danger"><i class="fas fa-triangle-exclamation"></i> ${item.prediction}</span></td>
                <td><strong>${conf}%</strong></td>
                <td><span class="${severityClass}">${severity}</span></td>
                <td><span style="color: #b91c1c; font-weight: 600;">${causes}</span></td>
                <td style="text-align: left; font-size: 12px; color: #475569; max-width: 300px;">${remark}</td>
                <td style="font-size: 12px; color: #64748b; white-space: nowrap;"><i class="fas fa-clock" style="color: #2563eb; margin-right: 4px;"></i>${formattedTime}</td>
            </tr>
        `;
    }).join("");

    document.getElementById("alertsTableBody").innerHTML = html;
    document.getElementById("alertPageNumber").innerText = `Page ${currentPage} of ${totalPages}`;

    document.getElementById("nextAlertBtn").disabled = currentPage >= totalPages;
    document.getElementById("prevAlertBtn").disabled = currentPage <= 1;
}

function renderNotification() {
    const notification = document.getElementById("alertsNotification");
    if (!notification) return;

    notification.classList.remove("notification-warning", "notification-success");

    if (alerts.length > 0) {
        notification.classList.add("notification-warning");
        notification.innerHTML = `
            <i class="fas fa-triangle-exclamation"></i>
            <span><strong>${alerts.length} active anomaly alert${alerts.length === 1 ? "" : "s"}</strong> streaming from live server infrastructure. Review high-severity incidents immediately.</span>
        `;
        return;
    }

    notification.classList.add("notification-success");
    notification.innerHTML = `
        <i class="fas fa-circle-check"></i>
        <span><strong>All 22 servers are operating normally.</strong> Zero anomalous telemetry signatures detected at this time.</span>
    `;
}

// Event Listeners
document.getElementById("nextAlertBtn").addEventListener("click", () => {
    const totalPages = Math.max(1, Math.ceil(filteredAlerts.length / recordsPerPage));
    if (currentPage < totalPages) {
        currentPage++;
        renderTable();
    }
});

document.getElementById("prevAlertBtn").addEventListener("click", () => {
    if (currentPage > 1) {
        currentPage--;
        renderTable();
    }
});

const searchInput = document.getElementById("searchAlertBox");
if (searchInput) {
    searchInput.addEventListener("input", () => {
        currentPage = 1;
        applyFilters();
        renderTable();
    });
}

// Severity filter buttons
const filterPills = document.querySelectorAll("#severityFilters .filter-pill");
filterPills.forEach(btn => {
    btn.addEventListener("click", () => {
        filterPills.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        activeSeverityFilter = btn.getAttribute("data-severity");
        currentPage = 1;
        applyFilters();
        renderTable();
    });
});

// Export CSV for alerts
const exportBtn = document.getElementById("exportAlertsBtn");
if (exportBtn) {
    exportBtn.addEventListener("click", () => {
        if (alerts.length === 0) {
            alert("No active alerts to export.");
            return;
        }

        const headers = ["Server Name", "Prediction", "Confidence", "Severity", "Causes", "Remark", "Timestamp (IST)"];
        const rows = alerts.map(a => {
            let sev = "Medium";
            const conf = Number(a.confidence) || 0;
            if (conf >= 90) sev = "Critical";
            else if (conf >= 70) sev = "High";
            const time = formatAlertTime(a.timestamp);
            const causes = (a.possible_causes || []).join("; ");
            const remark = `"${(a.remark || '').replace(/"/g, '""')}"`;
            return [a.server_name, a.prediction, `${conf}%`, sev, `"${causes}"`, remark, `"${time}"`].join(",");
        });

        const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows].join("\n");
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `live_monitoring_alerts_${Date.now()}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });
}

// Initial load & 3-second live streaming polling loop
loadAlerts();
setInterval(loadAlerts, 3000);
