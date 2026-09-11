// PredictOps AI - Live Monitoring Alerts

let allAlerts = [];
let filteredAlerts = [];
let currentPage = 1;
const recordsPerPage = 10;
let currentSeverityFilter = "ALL";
let searchQuery = "";

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

async function loadAlerts() {
    try {
        const response = await fetch("/all-server-predictions");
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const predictions = await response.json();

        // Filter only anomaly detections
        allAlerts = (predictions || []).filter(item => item.prediction === "ANOMALY");

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

        const totalActiveEl = document.getElementById("totalActiveAlertsCount");
        const criticalEl = document.getElementById("criticalAlertsCount");
        const highEl = document.getElementById("highAlertsCount");
        const mediumEl = document.getElementById("mediumAlertsCount");

        if (totalActiveEl) totalActiveEl.innerText = allAlerts.length;
        if (criticalEl) criticalEl.innerText = totalCritical;
        if (highEl) highEl.innerText = totalHigh;
        if (mediumEl) mediumEl.innerText = totalMedium;

        // Notification bar summary
        const notifBar = document.getElementById("alertsNotification");
        if (notifBar) {
            if (allAlerts.length > 0) {
                notifBar.className = "notification-bar notification-warning";
                notifBar.innerHTML = `<i class="fas fa-triangle-exclamation"></i> <span><strong>${allAlerts.length} Active Incidents Detected:</strong> ${totalCritical} Critical (90%+), ${totalHigh} High, ${totalMedium} Moderate risk servers.</span>`;
            } else {
                notifBar.className = "notification-bar notification-success";
                notifBar.innerHTML = `<i class="fas fa-circle-check"></i> <span>All 22 monitored servers are running within healthy baselines. Zero critical alerts.</span>`;
            }
        }

        const syncEl = document.getElementById("alertsSyncTime");
        if (syncEl) {
            const now = new Date();
            syncEl.innerText = now.toLocaleTimeString("en-IN", {
                timeZone: "Asia/Kolkata",
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
                hour12: true
            }) + " (IST)";
        }

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
        const matchesSearch = !searchQuery || (item.server_name && item.server_name.toLowerCase().includes(searchQuery.toLowerCase()));

        return matchesSeverity && matchesSearch;
    });
}

function renderAlertsTable() {
    const tableBody = document.getElementById("alertsTableBody");
    if (!tableBody) return;

    const totalPages = Math.max(1, Math.ceil(filteredAlerts.length / recordsPerPage));

    if (currentPage > totalPages) {
        currentPage = totalPages;
    }

    const startIndex = (currentPage - 1) * recordsPerPage;
    const paginated = filteredAlerts.slice(startIndex, startIndex + recordsPerPage);

    if (paginated.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: #94a3b8; padding: 24px;">No active anomaly alerts matching filter.</td></tr>`;
        renderNumberedPagination("alertsPagination", 1, 1, () => {});
        return;
    }

    tableBody.innerHTML = paginated.map((item, index) => {
        const sNo = startIndex + index + 1;
        const globalIndex = startIndex + index;
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
                <td style="text-align: center; color: #64748b; font-weight: 700; font-size: 12.5px;">${sNo}</td>
                <td class="server-cell">
                    <div class="server-cell-badge">
                        <span class="server-icon-box"><i class="fas fa-server"></i></span>
                        <span class="server-name-text">${item.server_name}</span>
                    </div>
                </td>
                <td><span class="badge-danger"><i class="fas fa-triangle-exclamation"></i><span>${item.prediction}</span></span></td>
                <td><strong>${conf}%</strong></td>
                <td><span class="${severityClass}">${severity}</span></td>
                <td><span style="color: #b91c1c; font-weight: 600;">${causes}</span></td>
                <td style="text-align: left; font-size: 12px; color: #475569; max-width: 300px;">${remark}</td>
                <td style="font-size: 12px; color: #64748b; white-space: nowrap;"><i class="fas fa-calendar-day" style="color: #2563eb; margin-right: 5px;"></i>${formattedTime}</td>
                <td style="text-align: center;">
                    <button type="button" class="view-detail-btn" onclick="openAlertDetail(${globalIndex})">
                        <i class="fas fa-eye"></i> Details
                    </button>
                </td>
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

function initAlerts() {
    const searchBox = document.getElementById("searchAlertBox");
    if (searchBox) {
        searchBox.addEventListener("input", e => {
            searchQuery = e.target.value;
            currentPage = 1;
            applyFilters();
            renderAlertsTable();
        });
    }

    function setSeverityFilter(severity) {
        currentSeverityFilter = severity;
        currentPage = 1;
        document.querySelectorAll("#severityFilters .filter-pill").forEach(p => {
            p.classList.toggle("active", p.getAttribute("data-severity") === severity);
        });
        document.querySelectorAll(".alert-filter-card").forEach(c => {
            c.classList.toggle("active", c.getAttribute("data-severity-card") === severity);
        });
        applyFilters();
        renderAlertsTable();
    }

    document.querySelectorAll("#severityFilters .filter-pill").forEach(pill => {
        pill.addEventListener("click", () => {
            setSeverityFilter(pill.getAttribute("data-severity"));
        });
    });

    document.querySelectorAll(".alert-filter-card").forEach(card => {
        card.addEventListener("click", () => {
            setSeverityFilter(card.getAttribute("data-severity-card"));
        });
    });

    const exportBtn = document.getElementById("exportAlertsBtn");
    if (exportBtn) {
        exportBtn.addEventListener("click", () => {
            if (allAlerts.length === 0) {
                alert("No active alerts to export.");
                return;
            }

            const headers = ["#", "Server Name", "Prediction", "Confidence", "Severity", "Causes", "Remark", "Timestamp (IST)"];
            const rows = allAlerts.map((a, index) => {
                let sev = "Medium";
                let conf = Number(a.confidence) || 0;
                if (conf > 100) conf = conf / 100;
                conf = Math.round(conf * 10) / 10;
                if (conf >= 90) sev = "Critical";
                else if (conf >= 70) sev = "High";
                const time = formatAlertTime(a.timestamp);
                const causes = (a.possible_causes || []).join("; ");
                const remark = `"${(a.remark || '').replace(/"/g, '""')}"`;
                return [index + 1, a.server_name, a.prediction, `${conf}%`, sev, `"${causes}"`, remark, `"${time}"`].join(",");
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

    loadAlerts();
    setInterval(loadAlerts, 30000);
}

function openAlertDetail(itemIndex) {
    const item = filteredAlerts[itemIndex] || allAlerts[itemIndex];
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

    const modal = document.getElementById("alertDetailModal");
    if (!modal) return;

    // Server Name & Detected Time
    document.getElementById("modalServerName").innerText = item.server_name || "Unknown Server";
    document.getElementById("modalDetectedTime").innerHTML = `<i class="fas fa-clock" style="color: #2563eb; margin-right: 4px;"></i> Detected: <strong>${formatAlertTime(item.timestamp)}</strong>`;

    // Icon
    const iconContainer = document.getElementById("modalSeverityIcon");
    if (iconContainer) {
        iconContainer.style.background = iconBg;
        iconContainer.style.color = iconColor;
        iconContainer.innerHTML = `<i class="fas ${iconClass}"></i>`;
    }

    // Badges
    const predBadge = document.getElementById("modalPredictionBadge");
    if (predBadge) {
        predBadge.className = item.prediction === "ANOMALY" ? "badge-danger" : "badge-success";
        predBadge.innerHTML = `<i class="fas ${item.prediction === 'ANOMALY' ? 'fa-triangle-exclamation' : 'fa-circle-check'}"></i> ${item.prediction}`;
    }

    const sevBadge = document.getElementById("modalSeverityBadge");
    if (sevBadge) {
        sevBadge.className = severityClass;
        sevBadge.innerText = severity;
    }

    const confBadge = document.getElementById("modalConfidenceBadge");
    if (confBadge) {
        confBadge.innerText = `${conf}% Confidence`;
    }

    // Telemetry metrics snapshot with dynamic color coding
    const cpuVal = item.cpu_usage_percent !== undefined && item.cpu_usage_percent !== null ? Number(item.cpu_usage_percent) : null;
    const memVal = item.memory_usage_percent !== undefined && item.memory_usage_percent !== null ? Number(item.memory_usage_percent) : null;
    const diskVal = item.disk_usage_percent !== undefined && item.disk_usage_percent !== null ? Number(item.disk_usage_percent) : null;

    const modalCpuEl = document.getElementById("modalCpu");
    const modalMemEl = document.getElementById("modalMem");
    const modalDiskEl = document.getElementById("modalDisk");

    if (modalCpuEl) {
        modalCpuEl.innerText = cpuVal !== null && !isNaN(cpuVal) ? `${cpuVal}%` : "--";
        modalCpuEl.style.color = cpuVal !== null && !isNaN(cpuVal) ? (cpuVal > 80 ? "#dc2626" : cpuVal > 60 ? "#d97706" : "#16a34a") : "";
    }
    if (modalMemEl) {
        modalMemEl.innerText = memVal !== null && !isNaN(memVal) ? `${memVal}%` : "--";
        modalMemEl.style.color = memVal !== null && !isNaN(memVal) ? (memVal > 85 ? "#dc2626" : memVal > 70 ? "#d97706" : "#16a34a") : "";
    }
    if (modalDiskEl) {
        modalDiskEl.innerText = diskVal !== null && !isNaN(diskVal) ? `${diskVal}%` : "--";
        modalDiskEl.style.color = diskVal !== null && !isNaN(diskVal) ? (diskVal > 85 ? "#dc2626" : diskVal > 70 ? "#d97706" : "#16a34a") : "";
    }
    
    let tp = "0.00 MB/s";
    if (item.network_throughput !== undefined && item.network_throughput !== null) {
        let num = Number(item.network_throughput);
        if (num > 100000) num = num / (1024 * 1024);
        tp = `${num.toFixed(2)} MB/s`;
    }
    document.getElementById("modalThroughput").innerText = tp;

    // Causes List
    const causesList = document.getElementById("modalCausesList");
    if (causesList) {
        const causes = (item.possible_causes && item.possible_causes.length > 0)
            ? item.possible_causes
            : ["Behavioral Telemetry Deviation (Resource Load Spike)"];
        causesList.innerHTML = causes.map(c => `<li>${c}</li>`).join("");
    }

    // AI Remark
    const fallbackRemark = `${severity}: resource deviation (${conf}% confidence). Urgent review recommended.`;
    const remark = item.remark || fallbackRemark;
    document.getElementById("modalRemark").innerHTML = `<strong>Status Assessment:</strong> ${remark}<br><br><strong>Action Item:</strong> Isolate worker threads on ${item.server_name}, investigate high-CPU/Memory PID allocations, and balance incoming requests.`;

    modal.style.display = "flex";
}

function closeAlertModal() {
    const modal = document.getElementById("alertDetailModal");
    if (modal) {
        modal.style.display = "none";
    }
}

// Close modal on click outside or Escape key
document.addEventListener("click", e => {
    const modal = document.getElementById("alertDetailModal");
    if (modal && e.target === modal) {
        closeAlertModal();
    }
});

document.addEventListener("keydown", e => {
    if (e.key === "Escape") {
        closeAlertModal();
    }
});

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAlerts);
} else {
    initAlerts();
}
