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

        filteredServers = servers;

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
         pageNumber.innerText = currentPage;
}
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

    const text = e.target.value.toLowerCase();

        filteredServers =
            servers.filter(server =>
                server.server_name
                    .toLowerCase()
                    .includes(text)
            );

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