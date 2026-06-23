let servers = [];
let filteredServers = [];
let currentPage = 1;

const recordsPerPage = 10;

async function loadServers() {

    try {

        const response =
            await fetch("/all-servers");

        servers =
            await response.json();

        console.log("Servers Loaded:", servers);

        applyServerFilter();

        renderTable();

    } catch(error) {

        console.error(
            "Error loading servers:",
            error
        );
    }
}

function renderTable() {

    const start =
        (currentPage - 1) *
        recordsPerPage;

    const end =
        start +
        recordsPerPage;

    const pageData =
        filteredServers.slice(
            start,
            end
        );

    const totalPages =
        Math.max(
            1,
            Math.ceil(
                filteredServers.length /
                recordsPerPage
            )
        );

    if(currentPage > totalPages){
        currentPage = totalPages;
    }

    let html = "";

    pageData.forEach(server => {

        html += `
        <tr>
            <td>${server.server_name}</td>
            <td>${server.cpu_usage_percent}%</td>
            <td>${server.memory_usage_percent}%</td>
            <td>${server.disk_usage_percent}%</td>
        </tr>
        `;
    });

    const tableBody =
    document.getElementById("serverTableBody");

      if (tableBody) {
       tableBody.innerHTML = html;
}

    const pageNumber =
    document.getElementById("pageNumber");

       if (pageNumber) {
         pageNumber.innerText =
            `Page ${currentPage} of ${totalPages}`;
}

    updateServerSummary();

    if(nextBtn){
        nextBtn.disabled =
            currentPage >= totalPages;
    }

    if(prevBtn){
        prevBtn.disabled =
            currentPage <= 1;
    }
}

function updateServerSummary() {

    const totalServers =
        servers.length;

    const averageCpu =
        totalServers === 0
        ? 0
        : Math.round(
            servers.reduce(
                (sum, server) =>
                sum + Number(server.cpu_usage_percent || 0),
                0
            ) / totalServers
        );

    const highCpuServers =
        servers.filter(
            server =>
            Number(server.cpu_usage_percent || 0) >= 80
        );

    const totalCount =
        document.getElementById("serverTotalCount");

    if(totalCount){
        totalCount.innerText = totalServers;
    }

    const averageCpuElement =
        document.getElementById("serverAverageCpu");

    if(averageCpuElement){
        averageCpuElement.innerText =
            `${averageCpu}%`;
    }

    const highCpuCount =
        document.getElementById("serverHighCpuCount");

    if(highCpuCount){
        highCpuCount.innerText =
            highCpuServers.length;
    }

    const notification =
        document.getElementById("serverNotification");

    if(!notification){
        return;
    }

    notification.classList.remove(
        "notification-warning",
        "notification-success"
    );

    if(highCpuServers.length > 0){

        notification.classList.add(
            "notification-warning"
        );

        notification.innerHTML =
            `<i class="fas fa-triangle-exclamation"></i>
             <span>${highCpuServers.length} server${highCpuServers.length === 1 ? "" : "s"} above 80% CPU. Review capacity before the next workload spike.</span>`;

        return;
    }

    notification.classList.add(
        "notification-success"
    );

    notification.innerHTML =
        `<i class="fas fa-circle-check"></i>
         <span>All monitored servers are below the high CPU threshold right now.</span>`;
}

function applyServerFilter() {

    const searchBox =
        document.getElementById("searchBox");

    const text =
        searchBox
        ? searchBox.value.toLowerCase()
        : "";

    filteredServers =
        servers.filter(server =>
            server.server_name
                .toLowerCase()
                .includes(text)
        );
}


    const nextBtn = document.getElementById("nextBtn");
        if (nextBtn) {
            nextBtn.addEventListener("click", () => {

        if (
            currentPage <
            Math.ceil(filteredServers.length / recordsPerPage)
        ) {
            currentPage++;
            renderTable();
        }
    });
}

    const prevBtn = document.getElementById("prevBtn");
        if (prevBtn) {
            prevBtn.addEventListener("click", () => {

        if (currentPage > 1) {
            currentPage--;
            renderTable();
        }
    });
}

    const searchBox = document.getElementById("searchBox");
        if (searchBox) {
            searchBox.addEventListener("input", e => {

        applyServerFilter();

        currentPage = 1;

        renderTable();
    });
}

    


    const exportBtn =
    document.getElementById("exportBtn");

      if (exportBtn) {
       exportBtn.addEventListener("click", () => {

        let csv =
            "Server,CPU,Memory,Disk\n";

        filteredServers.forEach(server => {

            csv +=
                `${server.server_name},${server.cpu_usage_percent},${server.memory_usage_percent},${server.disk_usage_percent}\n`;
        });

        const blob =
            new Blob([csv], {
                type: "text/csv"
            });

        const url =
            URL.createObjectURL(blob);

        const a =
            document.createElement("a");

        a.href = url;
        a.download =
            "server_report.csv";

        a.click();
    });
}

loadServers();

setInterval(
    loadServers,
    3000
);
