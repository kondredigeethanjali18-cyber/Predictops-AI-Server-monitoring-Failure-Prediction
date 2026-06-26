let servers = [];
let filteredServers = [];
let currentPage = 1;

const recordsPerPage = 10;

async function loadServers() {
    try {
        const response = await fetch("/all-servers");
        servers = await response.json();

        applyServerFilter();
        renderTable();
    } catch(error) {
        console.error("Error loading servers:", error);
    }
}

function applyServerFilter() {
    const searchBox = document.getElementById("searchBox");
    const text = searchBox ? searchBox.value.toLowerCase() : "";

    filteredServers = servers.filter(server =>
        server.server_name.toLowerCase().includes(text)
    );
}

function renderTable() {
    const totalPages = Math.max(
        1,
        Math.ceil(filteredServers.length / recordsPerPage)
    );

    if(currentPage > totalPages) {
        currentPage = totalPages;
    }

    const start = (currentPage - 1) * recordsPerPage;
    const end = start + recordsPerPage;
    const pageData = filteredServers.slice(start, end);

    const html = pageData.map(server => `
        <tr>
            <td>${server.server_name}</td>
            <td>${server.cpu_usage_percent}%</td>
            <td>${server.memory_usage_percent}%</td>
            <td>${server.disk_usage_percent}%</td>
        </tr>
    `).join("");

    document.getElementById("serverTableBody").innerHTML = html;
    document.getElementById("pageNumber").innerText =
        `Page ${currentPage} of ${totalPages}`;

    document.getElementById("nextBtn").disabled =
        currentPage >= totalPages;
    document.getElementById("prevBtn").disabled =
        currentPage <= 1;

    updateServerSummary();
}

function updateServerSummary() {
    const totalServers = servers.length;
    const averageCpu = totalServers === 0
        ? 0
        : Math.round(
            servers.reduce(
                (sum, server) =>
                sum + Number(server.cpu_usage_percent || 0),
                0
            ) / totalServers
        );

    const highCpuServers = servers.filter(
        server => Number(server.cpu_usage_percent || 0) >= 80
    );

    document.getElementById("serverTotalCount").innerText = totalServers;
    document.getElementById("serverAverageCpu").innerText = `${averageCpu}%`;
    document.getElementById("serverHighCpuCount").innerText =
        highCpuServers.length;

    const notification = document.getElementById("serverNotification");
    notification.classList.remove("notification-warning", "notification-success");

    if(highCpuServers.length > 0) {
        notification.classList.add("notification-warning");
        notification.innerHTML =
            `<i class="fas fa-triangle-exclamation"></i>
             <span>${highCpuServers.length} server${highCpuServers.length === 1 ? "" : "s"} above 80% CPU. Review capacity before the next workload spike.</span>`;
        return;
    }

    notification.classList.add("notification-success");
    notification.innerHTML =
        `<i class="fas fa-circle-check"></i>
         <span>All monitored servers are below the high CPU threshold right now.</span>`;
}

document.getElementById("nextBtn").addEventListener("click", () => {
    const totalPages = Math.max(
        1,
        Math.ceil(filteredServers.length / recordsPerPage)
    );

    if(currentPage < totalPages) {
        currentPage++;
        renderTable();
    }
});

document.getElementById("prevBtn").addEventListener("click", () => {
    if(currentPage > 1) {
        currentPage--;
        renderTable();
    }
});

document.getElementById("searchBox").addEventListener("input", () => {
    applyServerFilter();
    currentPage = 1;
    renderTable();
});

document.getElementById("exportBtn").addEventListener("click", () => {
    let csv = "Server,CPU,Memory,Disk\n";

    filteredServers.forEach(server => {
        csv +=
            `${server.server_name},${server.cpu_usage_percent},${server.memory_usage_percent},${server.disk_usage_percent}\n`;
    });

    const blob = new Blob([csv], {
        type: "text/csv"
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");

    a.href = url;
    a.download = "server_report.csv";
    a.click();

    URL.revokeObjectURL(url);
});

loadServers();

setInterval(
    loadServers,
    3000
);
