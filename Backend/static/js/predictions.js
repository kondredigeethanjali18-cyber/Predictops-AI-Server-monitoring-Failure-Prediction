let allPredictions = [];
let filteredPredictions = [];
let currentPage = 1;
const recordsPerPage = 10;

function formatPredictionTime(timestamp) {
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

async function loadPredictions() {
    try {
        const response = await fetch("/all-predictions");
        allPredictions = await response.json();
        applyPredictionFilter();
        renderTable();
    } catch (error) {
        console.error("Error loading predictions:", error);
    }
}

function applyPredictionFilter() {
    const filter = document.getElementById("predictionFilter").value;
    if (filter === "all") {
        filteredPredictions = [...allPredictions];
    } else {
        filteredPredictions = allPredictions.filter(item => item.prediction === filter);
    }
}

function renderTable() {
    const tableBody = document.getElementById("predictionTableBody");
    const totalPages = Math.max(1, Math.ceil(filteredPredictions.length / recordsPerPage));

    if (currentPage > totalPages) {
        currentPage = totalPages;
    }

    const startIndex = (currentPage - 1) * recordsPerPage;
    const paginated = filteredPredictions.slice(startIndex, startIndex + recordsPerPage);

    if (paginated.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: #94a3b8; padding: 24px;">No predictions recorded yet.</td></tr>`;
        renderNumberedPagination("predictionPagination", 1, 1, () => {});
        return;
    }

    tableBody.innerHTML = paginated.map(item => {
        let conf = item.confidence !== undefined ? Number(item.confidence) : 90;
        if (conf > 100) conf = conf / 100;
        conf = Math.round(conf * 10) / 10;

        const badge = item.prediction === "ANOMALY"
            ? `<span class="badge-danger"><i class="fas fa-triangle-exclamation"></i> <span>ANOMALY</span></span>`
            : `<span class="badge-success"><i class="fas fa-circle-check"></i> <span>NORMAL</span></span>`;

        const cpu = item.cpu_usage_percent !== undefined ? `${item.cpu_usage_percent}%` : "--";
        const mem = item.memory_usage_percent !== undefined ? `${item.memory_usage_percent}%` : "--";
        const disk = item.disk_usage_percent !== undefined ? `${item.disk_usage_percent}%` : "--";
        const throughput = formatThroughput(item.network_throughput);
        const time = formatPredictionTime(item.timestamp);

        return `
            <tr>
                <td><strong style="color: #0f172a;"><i class="fas fa-server" style="color: #64748b; margin-right: 6px;"></i>${item.server_name}</strong></td>
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
    // Prev button
    html += `<button class="page-nav-btn" ${currPage === 1 ? "disabled" : ""} data-page="${currPage - 1}"><i class="fas fa-chevron-left"></i> Prev</button>`;

    // Window logic for 10 buttons
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

    // Next button
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

document.getElementById("predictionFilter").addEventListener("change", () => {
    applyPredictionFilter();
    currentPage = 1;
    renderTable();
});

loadPredictions();
setInterval(loadPredictions, 8000);
