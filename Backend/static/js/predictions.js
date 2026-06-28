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
                <td>${item.cpu_usage_percent}%</td>
                <td>${item.memory_usage_percent}%</td>
                <td>${item.disk_usage_percent}%</td>
                <td>${item.timestamp}</td>
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
