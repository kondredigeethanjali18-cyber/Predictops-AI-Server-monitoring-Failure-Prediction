let servers = [];
let currentPage = 1;
const recordsPerPage = 10;

async function loadServers() {

    const response =
        await fetch("/all-servers");

    servers =
        await response.json();

    renderTable();
}

function renderTable() {

    const start =
        (currentPage - 1) *
        recordsPerPage;

    const end =
        start +
        recordsPerPage;

    const pageData =
        servers.slice(start, end);

    let html = "";

    pageData.forEach(server => {

        html += `
        <tr>
            <td>${server.server_name}</td>
            <td>${server.prediction || "--"}</td>
            <td>${server.confidence || "--"}%</td>
            <td>${server.cpu_usage_percent}%</td>
            <td>${server.memory_usage_percent}%</td>
            <td>${server.disk_usage_percent}%</td>
        </tr>
        `;
    });

    document.getElementById(
        "serverTableBody"
    ).innerHTML = html;

    document.getElementById(
        "pageNumber"
    ).innerText = currentPage;
}

document
.getElementById("nextBtn")
.addEventListener("click", () => {

    if (
        currentPage <
        Math.ceil(
            servers.length /
            recordsPerPage
        )
    ) {
        currentPage++;
        renderTable();
    }
});

document
.getElementById("prevBtn")
.addEventListener("click", () => {

    if (currentPage > 1) {

        currentPage--;

        renderTable();
    }
});

loadServers();

setInterval(
    loadServers,
    3000
);