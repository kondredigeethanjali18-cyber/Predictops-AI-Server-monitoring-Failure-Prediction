let allServers = [];
let filteredServers = [];
let currentPage = 1;
const serversPerPage = 10;

async function loadServers() {
    try {
        const response = await fetch("/all-servers");
        allServers = await response.json();

        document.getElementById("serverTotalCount").innerText = allServers.length;

        let totalCpu = 0;
        let highCount = 0;

        allServers.forEach(server => {
            const cpu = Number(server.cpu_usage_percent) || 0;
            totalCpu += cpu;
            if (cpu > 80) highCount++;
        });

        const count = allServers.length || 1;
        document.getElementById("serverAverageCpu").innerText = (totalCpu / count).toFixed(1) + "%";
        document.getElementById("serverHighCpuCount").innerText = highCount;

        const notif = document.getElementById("serverNotification");
        if (highCount > 0) {
            notif.className = "notification-bar notification-warning";
            notif.innerHTML = `<i class="fas fa-triangle-exclamation"></i> <span><strong>${highCount} servers</strong> are currently experiencing high utilization (>80%).</span>`;
        } else {
            notif.className = "notification-bar notification-success";
            notif.innerHTML = `<i class="fas fa-circle-check"></i> <span>All ${allServers.length} servers are operating within healthy resource parameters.</span>`;
        }

        applyServerFilter();
        renderTable();

    } catch (error) {
        console.error("Error loading servers:", error);
    }
}

function applyServerFilter() {
    const searchVal = document.getElementById("searchBox").value.toLowerCase();
    if (!searchVal) {
        filteredServers = [...allServers];
    } else {
        filteredServers = allServers.filter(s => s.server_name.toLowerCase().includes(searchVal));
    }
}

function renderTable() {
    const tableBody = document.getElementById("serverTableBody");
    const totalPages = Math.max(1, Math.ceil(filteredServers.length / serversPerPage));

    if (currentPage > totalPages) {
        currentPage = totalPages;
    }

    const startIndex = (currentPage - 1) * serversPerPage;
    const paginated = filteredServers.slice(startIndex, startIndex + serversPerPage);

    if (paginated.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: #94a3b8; padding: 24px;">No servers found.</td></tr>`;
        renderNumberedPagination("serversPagination", 1, 1, () => {});
        return;
    }

    tableBody.innerHTML = paginated.map(server => {
        const cpu = Number(server.cpu_usage_percent) || 0;
        const mem = Number(server.memory_usage_percent) || 0;
        const disk = Number(server.disk_usage_percent) || 0;

        const cpuColor = cpu > 80 ? "#dc2626" : cpu > 60 ? "#d97706" : "#16a34a";
        const memColor = mem > 85 ? "#dc2626" : mem > 70 ? "#d97706" : "#16a34a";

        return `
            <tr>
                <td><strong style="color: #0f172a;"><i class="fas fa-server" style="color: #64748b; margin-right: 6px;"></i>${server.server_name}</strong></td>
                <td><strong style="color: ${cpuColor};">${cpu}%</strong></td>
                <td><strong style="color: ${memColor};">${mem}%</strong></td>
                <td>${disk}%</td>
            </tr>
        `;
    }).join("");

    renderNumberedPagination("serversPagination", currentPage, totalPages, newPage => {
        currentPage = newPage;
        renderTable();
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

document.getElementById("searchBox").addEventListener("input", () => {
    applyServerFilter();
    currentPage = 1;
    renderTable();
});

document.getElementById("exportBtn").addEventListener("click", () => {
    let csv = "Server,CPU,Memory,Disk\n";
    filteredServers.forEach(server => {
        csv += `${server.server_name},${server.cpu_usage_percent},${server.memory_usage_percent},${server.disk_usage_percent}\n`;
    });
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `server_inventory_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
});

loadServers();
setInterval(loadServers, 8000);
