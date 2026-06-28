let predictions = [];
let filteredPredictions = [];

let currentPage = 1;
const recordsPerPage = 10;

async function loadPredictions() {
    try {
        const response = await fetch("/all-predictions");
        predictions = await response.json();

        applyPredictionFilter();
        renderTable();
    } catch(error) {
        console.error("Error loading predictions:", error);
    }
}

function applyPredictionFilter() {
    const filter = document.getElementById("predictionFilter").value;

    filteredPredictions = filter === "all"
        ? predictions
        : predictions.filter(p => p.prediction === filter);
}

function renderTable() {
    const totalPages = Math.max(
        1,
        Math.ceil(filteredPredictions.length / recordsPerPage)
    );

    if(currentPage > totalPages) {
        currentPage = totalPages;
    }

    const start = (currentPage - 1) * recordsPerPage;
    const end = start + recordsPerPage;
    const pageData = filteredPredictions.slice(start, end);

    const html = pageData.map(item => {
        const badge = item.prediction === "ANOMALY"
            ? '<span class="badge-danger">ANOMALY</span>'
            : '<span class="badge-success">NORMAL</span>';

        return `
            <tr>
                <td>${item.server_name}</td>
                <td>${badge}</td>
                <td>${item.confidence}%</td>
                <td>${formatPercent(item.cpu_usage_percent)}</td>
                <td>${formatPercent(item.memory_usage_percent)}</td>
                <td>${formatPercent(item.disk_usage_percent)}</td>
                <td>${formatNetworkThroughput(item)}</td>
                <td class="timestamp-cell">${formatPredictionTime(item.timestamp)}</td>
            </tr>
        `;
    }).join("");

    document.getElementById("predictionTableBody").innerHTML = html;
    document.getElementById("predictionPageNumber").innerText =
        `Page ${currentPage} of ${totalPages}`;

    document.getElementById("nextPredictionBtn").disabled =
        currentPage >= totalPages;
    document.getElementById("prevPredictionBtn").disabled =
        currentPage <= 1;
}

function formatPredictionTime(timestamp) {
    if(!timestamp) {
        return "Time unavailable";
    }

    const date = new Date(timestamp);

    if(Number.isNaN(date.getTime())) {
        return timestamp;
    }

    const year =
        date.getFullYear();

    const month =
        date.toLocaleString(
            [],
            {
                month: "long"
            }
        );

    const day =
        date.getDate();

    const time =
        date.toLocaleString(
            [],
            {
                hour: "2-digit",
                minute: "2-digit"
            }
        );

    return `${year} ${month} ${day}, ${time}`;
}

function formatPercent(value) {
    if(value === undefined || value === null || value === "") {
        return "N/A";
    }

    const number = Number(value);

    if(Number.isNaN(number)) {
        return `${value}%`;
    }

    return `${number.toFixed(1)}%`;
}

function formatNetworkThroughput(item) {
    const throughput =
        item.network_throughput ??
        item.network_throughput_mb_s ??
        getThroughputFromNetworkTotal(item) ??
        getCombinedThroughput(item);

    if(throughput === undefined || throughput === null || throughput === "") {
        return "N/A";
    }

    const number = Number(throughput);

    if(Number.isNaN(number)) {
        return throughput;
    }

    return `${number.toFixed(2)} MB/s`;
}

function getThroughputFromNetworkTotal(item) {
    const total =
        item.network_total ??
        item.network_load;

    if(total === undefined || total === null || total === "") {
        return undefined;
    }

    return normalizeNetworkVolumeToMb(total) / 5;
}

function getCombinedThroughput(item) {
    const sent =
        item.network_sent_mb;

    const received =
        item.network_received_mb;

    if(sent !== undefined && received !== undefined) {
        return (Number(sent) + Number(received)) / 5;
    }

    if(item.bytes_sent !== undefined && item.bytes_received !== undefined) {
        return (
            normalizeNetworkVolumeToMb(item.bytes_sent) +
            normalizeNetworkVolumeToMb(item.bytes_received)
        ) / 5;
    }

    return undefined;
}

function normalizeNetworkVolumeToMb(value) {
    const number =
        Number(value);

    if(Number.isNaN(number)) {
        return 0;
    }

    return number > 100000
        ? number / (1024 * 1024)
        : number;
}

document.getElementById("predictionFilter").addEventListener("change", () => {
    applyPredictionFilter();
    currentPage = 1;
    renderTable();
});

document.getElementById("nextPredictionBtn").addEventListener("click", () => {
    const totalPages = Math.max(
        1,
        Math.ceil(filteredPredictions.length / recordsPerPage)
    );

    if(currentPage < totalPages) {
        currentPage++;
        renderTable();
    }
});

document.getElementById("prevPredictionBtn").addEventListener("click", () => {
    if(currentPage > 1) {
        currentPage--;
        renderTable();
    }
});

loadPredictions();

setInterval(
    loadPredictions,
    3000
);
