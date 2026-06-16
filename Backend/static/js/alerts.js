let alerts = [];
let filteredAlerts = [];

let currentPage = 1;
const recordsPerPage = 10;

async function loadAlerts() {

    try {

        const response =
            await fetch("/all-server-predictions");

        const predictions =
            await response.json();

        alerts = predictions.filter(
          item => item.prediction === "ANOMALY");

        alerts.sort((a, b) => b.confidence - a.confidence);
        filteredAlerts = alerts;

        renderTable();

    } catch(error) {

        console.error(
            "Error loading alerts:",
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
        filteredAlerts.slice(
            start,
            end
        );

    let html = "";

    pageData.forEach(item => {

        let severity = "";
        let severityClass = "";

        if(item.confidence >= 90){

            severity = "Critical";
            severityClass =
                "severity-critical";

        }
        else if(item.confidence >= 70){

            severity = "High";
            severityClass =
                "severity-high";

        }
        else{

            severity = "Medium";
            severityClass =
                "severity-medium";
        }

        html += `
        <tr>

            <td>${item.server_name}</td>

            <td>
                <span class="badge-danger">
                    ${item.prediction}
                </span>
            </td>

            <td>${item.confidence}%</td>

            <td>
                <span class="${severityClass}">
                    ${severity}
                </span>
            </td>

            <td>
                ${item.possible_causes.join(", ")}
            </td>

        </tr>
        `;
    });

    document.getElementById("alertsTableBody").innerHTML = html;

    const totalPages =
    Math.ceil(
        filteredAlerts.length /
        recordsPerPage
    ) || 1;

    document.getElementById("alertPageInfo").innerText =`Page ${currentPage} of ${totalPages}`;
}
    document.getElementById("prevAlertBtn").disabled =currentPage === 1;

    document.getElementById("nextAlertBtn").disabled =currentPage === totalPages;

    document.getElementById("nextAlertBtn").addEventListener("click", () => {

    if(
        currentPage <
        Math.ceil(
            filteredAlerts.length /
            recordsPerPage
        )
    ){

        currentPage++;

        renderTable();
    }
});


    document.getElementById("prevAlertBtn").addEventListener("click", () => {

    if(currentPage > 1){

        currentPage--;

        renderTable();
    }
});


loadAlerts();

setInterval(
    loadAlerts,
    3000
);