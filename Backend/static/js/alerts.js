let allAlerts = [];
let filteredAlerts = [];
let currentPage = 1;
const recordsPerPage = 10;
let currentSeverityFilter = "ALL";
let searchQuery = "";

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

async function loadAlerts() {
    try {
        const response = await fetch("/all-server-predictions");
        const predictions = await response.json();

        // Filter only anomalies
        allAlerts = predictions.filter(item => item.prediction === "ANOMALY");

        // Calculate KPI Counts
        let totalCritical = 0;
        let totalHigh = 0;
        let totalMedium = 0;

        allAlerts.forEach(item => {
            let conf = Number(item.confidence) || 0;
            if (conf > 100) conf = conf / 100;
            if (conf >= 90) totalCritical++;
            else if (conf >= 70) totalHigh++;
            else totalMedium++;
        });

        document.getElementById("totalActiveAlertsCount").innerText = allAlerts.length;
        document.getElementById("criticalAlertsCount").innerText = totalCritical;
        document.getElementById("highAlertsCount").innerText = totalHigh;
        document.getElementById("mediumAlertsCount").innerText = totalMedium;

        // Notification summary
        const notifBar = document.getElementById("alertsNotification");
        if (allAlerts.length > 0) {
            notifBar.className = "notification-bar notification-warning";
            notifBar.innerHTML = `<i class="fas fa-triangle-exclamation"></i> <span><strong>${allAlerts.length} Active Incidents:</strong> ${totalCritical} Critical, ${totalHigh} High, ${totalMedium} Moderate risk servers detected.</span>`;
        } else {
            notifBar.className = "notification-bar notification-success";
            notifBar.innerHTML = `<i class="fas fa-circle-check"></i> <span>All 22 monitored servers are running within healthy baselines. Zero critical alerts.</span>`;
        }

        const now = new Date();
        document.getElementById("alertsSyncTime").innerText = now.toLocaleTimeString("en-IN", {
            timeZone: "Asia/Kolkata",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: true
        }) + " (IST)";

        applyFilters();
        renderAlertsTable();

    } catch (error) {
        console.error("Error loading alerts:", error);
    }
}

function applyFilters() {
    filteredAlerts = allAlerts.filter(item => {
        let conf = Number(item.confidence) || 0;
        if (conf > 100) conf = conf / 100;

        let severity = "Medium";
        if (conf >= 90) severity = "Critical";
        else if (conf >= 70) severity = "High";

        const matchesSeverity = currentSeverityFilter === "ALL" || severity === currentSeverityFilter;
        const matchesSearch = !searchQuery || item.server_name.toLowerCase().includes(searchQuery.toLowerCase());

        return matchesSeverity && matchesSearch;
    });
}

function renderAlertsTable() {
    const tableBody = document.getElementById("alertsTableBody");
    const totalPages = Math.max(1, Math.ceil(filteredAlerts.length / recordsPerPage));

    if (currentPage > totalPages) {
        currentPage = totalPages;
    }

    const startIndex = (currentPage - 1) * recordsPerPage;
    const paginated = filteredAlerts.slice(startIndex, startIndex + recordsPerPage);

    if (paginated.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; color: #16a34a; padding: 24px;">
                    <i class="fas fa-circle-check" style="margin-right: 6px;"></i> No active anomaly alerts matching current filter.
                </td>
            </tr>
        `;
        renderNumberedPagination("alertsPagination", 1, 1, () => {});
        return;
    }

    tableBody.innerHTML = paginated.map(item => {
        let conf = item.confidence !== undefined ? Number(item.confidence) : 90;
        if (conf > 100) conf = conf / 100;
        conf = Math.round(conf * 10) / 10;

        let severity = "Moderate";
        let severityClass = "severity-medium";

        if (conf >= 90) {
            severity = "Critical";
            severityClass = "severity-critical";
        } else if (conf >= 70) {
            severity = "High";
            severityClass = "severity-high";
        }

        const fallbackRemark = `${severity}: resource deviation (${conf}% confidence). Urgent review recommended.`;
        const remark = item.remark || fallbackRemark;
        const formattedTime = formatAlertTime(item.timestamp);
        const causes = (item.possible_causes && item.possible_causes.length > 0)
            ? item.possible_causes.join(", ")
            : "Behavioral Telemetry Anomaly";

        return `
            <tr>
                <td><strong style="color: #0f172a;"><i class="fas fa-server" style="color: #64748b; margin-right: 6px;"></i>${item.server_name}</strong></td>
                <td><span class="badge-danger"><i class="fas fa-triangle-exclamation"></i><span>${item.prediction}</span></span></td>
                <td><strong>${conf}%</strong></td>
                <td><span class="${severityClass}">${severity}</span></td>
                <td><span style="color: #b91c1c; font-weight: 600;">${causes}</span></td>
                <td style="text-align: left; font-size: 12px; color: #475569; max-width: 300px;">${remark}</td>
                <td style="font-size: 12px; color: #64748b; white-space: nowrap;"><i class="fas fa-calendar-day" style="color: #2563eb; margin-right: 5px;"></i>${formattedTime}</td>
            </tr>
        `;
    }).join("");

    renderNumberedPagination("alertsPagination", currentPage, totalPages, newPage => {
        currentPage = newPage;
        renderAlertsTable();
    });
}

function renderNumberedPagination(containerId, currPage, totalPages, onPageClick) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (totalPages <= 1) {
        container.innerHTML = `
            <button class="page-nav-btn" disabled><i class="fas fa-chevron-left"></i> Prev</button>
            <button class="page-num-btn active">1</button>
            <button class="page-nav-btn" disabled>Next <i class="fas fa-chevron-right"></i></button>
            <span class="page-summary">Page 1 of 1</span>
        `;
        return;
    }

    let html = "";
    html += `<button class="page-nav-btn" ${currPage === 1 ? "disabled" : ""} data-page="${currPage - 1}"><i class="fas fa-chevron-left"></i> Prev</button>`;

    const maxBtns = 10;
    let startPage = 1;
    let endPage = totalPages;

    if (totalPages > maxBtns) {
        if (currPage <= 6) {
            startPage = 1;
            endPage = 9;
        } else if (currPage + 4 >= totalPages) {
            startPage = totalPages - 8;
            endPage = totalPages;
        } else {
            startPage = currPage - 4;
            endPage = currPage + 4;
        }
    }

    if (startPage > 1) {
        html += `<button class="page-num-btn" data-page="1">1</button>`;
        if (startPage > 2) {
            html += `<span class="page-ellipsis">...</span>`;
        }
    }

    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="page-num-btn ${i === currPage ? "active" : ""}" data-page="${i}">${i}</button>`;
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            html += `<span class="page-ellipsis">...</span>`;
        }
        html += `<button class="page-num-btn" data-page="${totalPages}">${totalPages}</button>`;
    }

    html += `<button class="page-nav-btn" ${currPage === totalPages ? "disabled" : ""} data-page="${currPage + 1}">Next <i class="fas fa-chevron-right"></i></button>`;
    html += `<span class="page-summary">Page ${currPage} of ${totalPages}</span>`;

    container.innerHTML = html;

    container.querySelectorAll("button[data-page]").forEach(btn => {
        btn.addEventListener("click", () => {
            const p = parseInt(btn.getAttribute("data-page"));
            if (!isNaN(p) && p >= 1 && p <= totalPages && p !== currPage) {
                onPageClick(p);
            }
        });
    });
}

// Search input listener
document.getElementById("searchAlertBox").addEventListener("input", e => {
    searchQuery = e.target.value;
    currentPage = 1;
    applyFilters();
    renderAlertsTable();
});

// Severity filter buttons listener
document.querySelectorAll("#severityFilters .filter-pill").forEach(pill => {
    pill.addEventListener("click", () => {
        document.querySelectorAll("#severityFilters .filter-pill").forEach(p => p.classList.remove("active"));
        pill.classList.add("active");
        currentSeverityFilter = pill.getAttribute("data-severity");
        currentPage = 1;
        applyFilters();
        renderAlertsTable();
    });
});

// Export CSV for alerts
const exportBtn = document.getElementById("exportAlertsBtn");
if (exportBtn) {
    exportBtn.addEventListener("click", () => {
        if (allAlerts.length === 0) {
            alert("No active alerts to export.");
            return;
        }

        const headers = ["Server Name", "Prediction", "Confidence", "Severity", "Causes", "Remark", "Timestamp (IST)"];
        const rows = allAlerts.map(a => {
            let sev = "Medium";
            let conf = Number(a.confidence) || 0;
            if (conf > 100) conf = conf / 100;
            conf = Math.round(conf * 10) / 10;
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

// Initial load & 8-second live streaming polling loop
loadAlerts();
setInterval(loadAlerts, 8000);
