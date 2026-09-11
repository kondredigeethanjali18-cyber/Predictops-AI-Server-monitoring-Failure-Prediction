let allPredictions = [];
let filteredPredictions = [];
let currentPage = 1;
const recordsPerPage = 10;
let currentDatePreset = "all";
let customStartDate = null;
let customEndDate = null;
let currentStatusFilter = "all";
let searchQuery = "";

function parseRecordDate(timestamp) {
    if (!timestamp) return null;
    let ts = String(timestamp).trim();
    if (ts.includes("T") && !ts.endsWith("Z") && !ts.includes("+") && !ts.includes("-", 10)) {
        ts += "Z";
    }
    const d = new Date(ts);
    return isNaN(d.getTime()) ? null : d;
}

function formatPredictionTime(timestamp) {
    const d = parseRecordDate(timestamp);
    if (!d) return timestamp || "Time unavailable";

    return d.toLocaleString("en-IN", {
        timeZone: "Asia/Kolkata",
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: true
    }) + " (IST)";
}

async function loadPredictions() {
    try {
        const response = await fetch("/all-predictions");
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        allPredictions = await response.json();

        updatePresetCounts();
        applyPredictionFilter();
        renderTable();
    } catch (error) {
        console.error("Error loading predictions:", error);
    }
}

function updatePresetCounts() {
    const countAllEl = document.getElementById("countRangeAll");
    const countTodayEl = document.getElementById("countRangeToday");

    if (countAllEl) countAllEl.innerText = allPredictions.length;

    if (countTodayEl) {
        const todayStr = new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD in local
        let todayCount = 0;
        allPredictions.forEach(p => {
            const d = parseRecordDate(p.timestamp);
            if (d && d.toLocaleDateString("en-CA") === todayStr) {
                todayCount++;
            }
        });
        countTodayEl.innerText = todayCount;
    }
}

function applyPredictionFilter() {
    const now = new Date();
    const todayStr = now.toLocaleDateString("en-CA");

    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    const yesterdayStr = yesterday.toLocaleDateString("en-CA");

    const sevenDaysAgo = new Date(now);
    sevenDaysAgo.setDate(now.getDate() - 7);

    filteredPredictions = allPredictions.filter(item => {
        // 1. Status Filter
        if (currentStatusFilter !== "all" && item.prediction !== currentStatusFilter) {
            return false;
        }

        // 2. Search Query (Server name)
        if (searchQuery) {
            const sName = (item.server_name || "").toLowerCase();
            if (!sName.includes(searchQuery.toLowerCase())) {
                return false;
            }
        }

        // 3. Date Range Filter
        const recordDate = parseRecordDate(item.timestamp);
        if (!recordDate) return true;

        if (currentDatePreset === "today") {
            return recordDate.toLocaleDateString("en-CA") === todayStr;
        } else if (currentDatePreset === "yesterday") {
            return recordDate.toLocaleDateString("en-CA") === yesterdayStr;
        } else if (currentDatePreset === "7days") {
            return recordDate >= sevenDaysAgo;
        } else if (currentDatePreset === "custom") {
            if (customStartDate && customEndDate) {
                const recDay = recordDate.toLocaleDateString("en-CA");
                return recDay >= customStartDate && recDay <= customEndDate;
            } else if (customStartDate) {
                const recDay = recordDate.toLocaleDateString("en-CA");
                return recDay >= customStartDate;
            } else if (customEndDate) {
                const recDay = recordDate.toLocaleDateString("en-CA");
                return recDay <= customEndDate;
            }
        }

        return true;
    });
}

function renderTable() {
    const tableBody = document.getElementById("predictionTableBody");
    if (!tableBody) return;

    const totalPages = Math.max(1, Math.ceil(filteredPredictions.length / recordsPerPage));

    if (currentPage > totalPages) {
        currentPage = totalPages;
    }

    const startIndex = (currentPage - 1) * recordsPerPage;
    const paginated = filteredPredictions.slice(startIndex, startIndex + recordsPerPage);

    if (paginated.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: #94a3b8; padding: 28px;">No prediction records matching the selected date or risk filter.</td></tr>`;
        renderNumberedPagination("predictionPagination", 1, 1, () => {});
        return;
    }

    tableBody.innerHTML = paginated.map((item, index) => {
        const sNo = startIndex + index + 1;
        let conf = item.confidence !== undefined ? Number(item.confidence) : 90;
        if (conf > 100) conf = conf / 100;
        conf = Math.round(conf * 10) / 10;

        const badge = item.prediction === "ANOMALY"
            ? `<span class="badge-danger"><i class="fas fa-triangle-exclamation"></i> <span>ANOMALY</span></span>`
            : `<span class="badge-success"><i class="fas fa-circle-check"></i> <span>NORMAL</span></span>`;

        const cpuNum = item.cpu_usage_percent !== undefined && item.cpu_usage_percent !== null ? Number(item.cpu_usage_percent) : null;
        const memNum = item.memory_usage_percent !== undefined && item.memory_usage_percent !== null ? Number(item.memory_usage_percent) : null;
        const diskNum = item.disk_usage_percent !== undefined && item.disk_usage_percent !== null ? Number(item.disk_usage_percent) : null;

        const cpuColor = cpuNum !== null && !isNaN(cpuNum) ? (cpuNum > 80 ? "#dc2626" : cpuNum > 60 ? "#d97706" : "#16a34a") : "#64748b";
        const memColor = memNum !== null && !isNaN(memNum) ? (memNum > 85 ? "#dc2626" : memNum > 70 ? "#d97706" : "#16a34a") : "#64748b";
        const diskColor = diskNum !== null && !isNaN(diskNum) ? (diskNum > 85 ? "#dc2626" : diskNum > 70 ? "#d97706" : "#16a34a") : "#64748b";

        const cpu = cpuNum !== null && !isNaN(cpuNum) ? `<strong style="color: ${cpuColor};">${cpuNum}%</strong>` : "--";
        const mem = memNum !== null && !isNaN(memNum) ? `<strong style="color: ${memColor};">${memNum}%</strong>` : "--";
        const disk = diskNum !== null && !isNaN(diskNum) ? `<strong style="color: ${diskColor};">${diskNum}%</strong>` : "--";
        const throughput = formatThroughput(item.network_throughput);
        const time = formatPredictionTime(item.timestamp);

        return `
            <tr>
                <td style="text-align: center; color: #64748b; font-weight: 700; font-size: 12.5px;">${sNo}</td>
                <td class="server-cell">
                    <div class="server-cell-badge">
                        <span class="server-icon-box"><i class="fas fa-server"></i></span>
                        <span class="server-name-text">${item.server_name}</span>
                    </div>
                </td>
                <td>${badge}</td>
                <td><strong>${conf}%</strong></td>
                <td>${cpu}</td>
                <td>${mem}</td>
                <td>${disk}</td>
                <td>${throughput}</td>
                <td style="font-size: 12px; color: #64748b; white-space: nowrap;"><i class="fas fa-calendar-day" style="color: #2563eb; margin-right: 5px;"></i>${time}</td>
            </tr>
        `;
    }).join("");


    renderNumberedPagination("predictionPagination", currentPage, totalPages, newPage => {
        currentPage = newPage;
        renderTable();
    });
}

function formatThroughput(value) {
    if (value === undefined || value === null || value === "") return "0.00 MB/s";
    let num = Number(value);
    if (isNaN(num)) return "0.00 MB/s";
    if (num > 100000) num = num / (1024 * 1024);
    return `${num.toFixed(2)} MB/s`;
}

function getTodayDateStr() {
    return new Date().toLocaleDateString("en-CA");
}

function showDateValidationError(msg) {
    const msgEl = document.getElementById("dateValidationMessage");
    const textEl = document.getElementById("dateValidationText");
    const startInput = document.getElementById("predStartDate");
    const endInput = document.getElementById("predEndDate");

    if (textEl) textEl.innerText = msg;
    if (msgEl) msgEl.classList.add("active");
    if (startInput) startInput.classList.add("date-input-error");
    if (endInput) endInput.classList.add("date-input-error");
}

function clearDateValidationError() {
    const msgEl = document.getElementById("dateValidationMessage");
    const textEl = document.getElementById("dateValidationText");
    const startInput = document.getElementById("predStartDate");
    const endInput = document.getElementById("predEndDate");

    if (textEl) textEl.innerText = "";
    if (msgEl) msgEl.classList.remove("active");
    if (startInput) startInput.classList.remove("date-input-error");
    if (endInput) endInput.classList.remove("date-input-error");
}

function setupDatePickerConstraints() {
    const today = getTodayDateStr();
    const startInput = document.getElementById("predStartDate");
    const endInput = document.getElementById("predEndDate");

    if (startInput) {
        startInput.max = today;
        startInput.addEventListener("input", () => {
            clearDateValidationError();
            const sVal = startInput.value;
            if (endInput) {
                endInput.min = sVal || "";
            }
        });
    }

    if (endInput) {
        endInput.max = today;
        endInput.addEventListener("input", () => {
            clearDateValidationError();
            const eVal = endInput.value;
            if (startInput) {
                startInput.max = eVal || today;
            }
        });
    }
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

function setDatePreset(range) {
    currentDatePreset = range;
    currentPage = 1;

    document.querySelectorAll("#datePresetGroup .filter-pill").forEach(p => {
        p.classList.toggle("active", p.getAttribute("data-range") === range);
    });

    const customRow = document.getElementById("customDateRangeRow");
    if (customRow) {
        customRow.style.display = range === "custom" ? "flex" : "none";
    }

    const summaryEl = document.getElementById("dateFilterSummary");
    if (summaryEl) {
        if (range === "today") summaryEl.innerText = "Showing today's telemetry";
        else if (range === "yesterday") summaryEl.innerText = "Showing yesterday's telemetry";
        else if (range === "7days") summaryEl.innerText = "Showing last 7 days";
        else if (range === "all") summaryEl.innerText = "";
    }

    applyPredictionFilter();
    renderTable();
}

function initPredictions() {
    setupDatePickerConstraints();

    // 1. Status Filter
    const filterEl = document.getElementById("predictionFilter");
    if (filterEl) {
        filterEl.addEventListener("change", e => {
            currentStatusFilter = e.target.value;
            currentPage = 1;
            applyPredictionFilter();
            renderTable();
        });
    }

    // 2. Search Box
    const searchEl = document.getElementById("predSearchBox");
    if (searchEl) {
        searchEl.addEventListener("input", e => {
            searchQuery = e.target.value.trim();
            currentPage = 1;
            applyPredictionFilter();
            renderTable();
        });
    }

    // 3. Preset Date Buttons
    document.querySelectorAll("#datePresetGroup .filter-pill").forEach(btn => {
        btn.addEventListener("click", () => {
            clearDateValidationError();
            setDatePreset(btn.getAttribute("data-range") || "all");
        });
    });

    // 4. Custom Date Range Pickers
    const btnApply = document.getElementById("btnApplyCustomDate");
    if (btnApply) {
        btnApply.addEventListener("click", () => {
            clearDateValidationError();
            const startInput = document.getElementById("predStartDate");
            const endInput = document.getElementById("predEndDate");
            const sVal = startInput ? startInput.value : "";
            const eVal = endInput ? endInput.value : "";
            const today = getTodayDateStr();

            if (!sVal && !eVal) {
                showDateValidationError("Please select at least a Start Date or an End Date.");
                return;
            }

            if (sVal && sVal > today) {
                showDateValidationError("Start date cannot be in the future. Please select today or an earlier date.");
                return;
            }

            if (eVal && eVal > today) {
                showDateValidationError("End date cannot be in the future. Please select today or an earlier date.");
                return;
            }

            if (sVal && eVal && sVal > eVal) {
                showDateValidationError("Start Date cannot be after End Date. Please specify a valid chronological range.");
                return;
            }

            customStartDate = sVal || null;
            customEndDate = eVal || null;

            const summaryEl = document.getElementById("dateFilterSummary");
            if (summaryEl) {
                if (sVal && eVal) summaryEl.innerText = `Filtered: ${sVal} to ${eVal}`;
                else if (sVal) summaryEl.innerText = `Filtered from ${sVal}`;
                else if (eVal) summaryEl.innerText = `Filtered up to ${eVal}`;
            }

            currentPage = 1;
            applyPredictionFilter();
            renderTable();
        });
    }

    const btnReset = document.getElementById("btnResetDateFilter");
    if (btnReset) {
        btnReset.addEventListener("click", () => {
            const today = getTodayDateStr();
            const startInput = document.getElementById("predStartDate");
            const endInput = document.getElementById("predEndDate");

            if (startInput) {
                startInput.value = "";
                startInput.max = today;
                startInput.min = "";
            }
            if (endInput) {
                endInput.value = "";
                endInput.max = today;
                endInput.min = "";
            }

            clearDateValidationError();
            customStartDate = null;
            customEndDate = null;
            setDatePreset("all");
        });
    }

    // 5. CSV Export
    const exportBtn = document.getElementById("exportPredictionsBtn");
    if (exportBtn) {
        exportBtn.addEventListener("click", () => {
            if (filteredPredictions.length === 0) {
                alert("No prediction records to export matching current filter.");
                return;
            }

            const headers = ["#", "Server Name", "Prediction", "Confidence (%)", "CPU (%)", "Memory (%)", "Disk (%)", "Network Throughput", "Timestamp (IST)"];
            const rows = filteredPredictions.map((p, index) => {
                let conf = Number(p.confidence) || 0;
                if (conf > 100) conf = conf / 100;
                conf = Math.round(conf * 10) / 10;
                const time = formatPredictionTime(p.timestamp);
                const tp = formatThroughput(p.network_throughput);
                return [
                    index + 1,
                    p.server_name,
                    p.prediction,
                    `${conf}%`,
                    `${p.cpu_usage_percent || 0}%`,
                    `${p.memory_usage_percent || 0}%`,
                    `${p.disk_usage_percent || 0}%`,
                    `"${tp}"`,
                    `"${time}"`
                ].join(",");
            });

            const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows].join("\n");
            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", `predictions_report_${Date.now()}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
    }

    loadPredictions();
    setInterval(loadPredictions, 30000);
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initPredictions);
} else {
    initPredictions();
}
