let cpuLabels = [];
let cpuValues = [];

let memoryLabels = [];
let memoryValues = [];

let currentPage = 1;
const rowsPerPage = 10;

let allServers = [];

/* ------------------ Charts ------------------ */

const cpuChart = new Chart(
    document.getElementById("cpuChart"),
    {
        type: "line",
        data: {
            labels: cpuLabels,
            datasets: [{
                label: "CPU %",
                data: cpuValues
            }]
        }
    }
);

const memoryChart = new Chart(
    document.getElementById("memoryChart"),
    {
        type: "line",
        data: {
            labels: memoryLabels,
            datasets: [{
                label: "Memory %",
                data: memoryValues
            }]
        }
    }
);

/* ------------------ Metrics ------------------ */

async function loadMetrics() {

    const response = await fetch(
        "/latest-metrics"
    );

    const data = await response.json();

    cpuLabels.push(
        new Date().toLocaleTimeString()
    );

    cpuValues.push(
        data.cpu_usage_percent
    );

    if (cpuLabels.length > 20) {
        cpuLabels.shift();
        cpuValues.shift();
    }

    cpuChart.update();

    memoryLabels.push(
        new Date().toLocaleTimeString()
    );

    memoryValues.push(
        data.memory_usage_percent
    );

    if (memoryLabels.length > 20) {
        memoryLabels.shift();
        memoryValues.shift();
    }

    memoryChart.update();

    document.getElementById("cpu").innerText =
        data.cpu_usage_percent + "%";

    document.getElementById("memory").innerText =
        data.memory_usage_percent + "%";

    document.getElementById("disk").innerText =
        data.disk_usage_percent + "%";

    document.getElementById("network").innerText =
        (
            data.network_sent_mb +
            data.network_received_mb
        ).toFixed(2) + " MB";
}

/* ------------------ Latest Prediction ------------------ */

async function loadPrediction() {

    const response = await fetch(
        "/latest-prediction"
    );

    const data = await response.json();

    document.getElementById("server").innerText =
        data.server_name;

    document.getElementById("status").innerText =
        data.prediction;

    document.getElementById("confidence").innerText =
        data.confidence + "%";

    if (data.prediction === "NORMAL") {

        document.getElementById("health").innerText =
            "🟢 Healthy";

    } else {

        document.getElementById("health").innerText =
            "🔴 Critical";
    }

    let causes = "";

    data.possible_causes.forEach(cause => {

        causes += `<li>${cause}</li>`;
    });

    document.getElementById("causes").innerHTML =
        causes;
}

/* ------------------ All Servers ------------------ */

async function loadServers() {

    const response = await fetch(
        "/all-server-predictions"
    );

    allServers = await response.json();

    document.getElementById(
        "totalServers"
    ).innerText = allServers.length;

    renderTable();
    renderAlerts();
}

/* ------------------ Pagination ------------------ */

function renderTable() {

    const start =
        (currentPage - 1) * rowsPerPage;

    const end =
        start + rowsPerPage;

    const pageServers =
        allServers.slice(start, end);

    let html = "";

    pageServers.forEach(server => {

        html += `
        <tr>
            <td>${server.server_name}</td>
            <td>${server.prediction}</td>
            <td>${server.confidence}%</td>
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

/* ------------------ Alerts ------------------ */

function renderAlerts() {

    let html = "";

    const alerts =
        allServers.filter(
            s => s.prediction !== "NORMAL"
        );

    if (alerts.length === 0) {

        html =
            "<li>No Active Alerts</li>";

    } else {

        alerts.forEach(server => {

            html += `
            <li>
                ${server.server_name}
                - ${server.prediction}
            </li>
            `;
        });
    }

    document.getElementById(
        "alerts"
    ).innerHTML = html;
}

/* ------------------ Buttons ------------------ */

document
.getElementById("prevBtn")
.addEventListener("click", () => {

    if (currentPage > 1) {

        currentPage--;

        renderTable();
    }
});

document
.getElementById("nextBtn")
.addEventListener("click", () => {

    const maxPage =
        Math.ceil(
            allServers.length /
            rowsPerPage
        );

    if (currentPage < maxPage) {

        currentPage++;

        renderTable();
    }
});

async function loadDashboard() {

    const response =
        await fetch(
            "/all-predictions"
        );

    const data =
        await response.json();

    let healthy = 0;
    let warning = 0;
    let critical = 0;

    data.forEach(server => {

        const cpu =
            server.cpu_usage_percent;

        const memory =
            server.memory_usage_percent;

        if(cpu > 90 || memory > 90){

            critical++;

        } else if(cpu > 70 || memory > 80){

            warning++;

        } else {

            healthy++;
        }
    });

    document.getElementById(
        "totalServers"
    ).innerText =
        data.length;

    document.getElementById(
        "healthyServers"
    ).innerText =
        healthy;

    document.getElementById(
        "warningServers"
    ).innerText =
        warning;

    document.getElementById(
        "criticalServers"
    ).innerText =
        critical;
}

loadDashboard();

setInterval(
    loadDashboard,
    3000
);
/* ------------------ Refresh ------------------ */

// async function refreshDashboard() {

//     await loadMetrics();

//     await loadPrediction();

//     await loadServers();
// }

// refreshDashboard();

// setInterval(
//     refreshDashboard,
//     3000
// );