let cpuLabels = [];
let cpuValues = [];
let memoryLabels = [];
let memoryValues = [];

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





async function loadMetrics() {

    const response = await fetch(
        "http://127.0.0.1:8000/latest-metrics"
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


    document.getElementById("cpu").innerText =
        data.cpu_usage_percent + "%";

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

    document.getElementById("memory").innerText =
        data.memory_usage_percent + "%";

    document.getElementById("disk").innerText =
        data.disk_usage_percent + "%";

    document.getElementById("network").innerText =
        (
            data.network_sent_mb +
            data.network_received_mb
        ).toFixed(2) + " MB";

    document.getElementById("totalServers").innerText = 1;
}


async function loadPrediction() {


    const response = await fetch(
        "http://127.0.0.1:8000/latest-prediction"
    );


    const data = await response.json();

    if(data.prediction === "NORMAL"){
    document.getElementById("health").innerText =
        "🟢 Healthy";
}
    else{
    document.getElementById("health").innerText =
        "🔴 Critical";
}

    document.getElementById("server").innerText =
        data.server_name;

    document.getElementById("status").innerText =
        data.prediction;

    document.getElementById("confidence").innerText =
        data.confidence + "%";

    let causes = "";

    if (data.possible_causes) {

        data.possible_causes.forEach(cause => {

            causes += `<li>${cause}</li>`;
        });
    }

    document.getElementById("causes").innerHTML =
        causes;

    document.getElementById("serverTableBody").innerHTML =
    `
    <tr>
    <td>${data.server_name}</td>
    <td>${data.prediction}</td>
    <td>${document.getElementById("cpu").innerText}</td>
    <td>${document.getElementById("memory").innerText}</td>
     </tr>`;

    let alerts = [];

    if(data.prediction !== "NORMAL"){

    alerts.push(
        `${data.server_name} : ${data.prediction}`
    );
}

    let alertHtml = "";

    alerts.forEach(alert => {
    alertHtml += `<li>${alert}</li>`;
});

    if(alertHtml === ""){
    alertHtml =
        "<li>No Active Alerts</li>";
}

document.getElementById("alerts").innerHTML =
    alertHtml;
}

async function refreshDashboard() {

    await loadMetrics();
    await loadPrediction();
}

refreshDashboard();

setInterval(
    refreshDashboard,
    5000
);