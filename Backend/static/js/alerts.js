let alerts = [];
let filteredAlerts = [];

let currentPage = 1;
const recordsPerPage = 10;

async function loadAlerts() {
    try {
        const response = await fetch("/all-server-predictions");
        const predictions = await response.json();

        alerts = predictions
            .filter(item => item.prediction === "ANOMALY")
            .sort((a, b) => b.confidence - a.confidence);

        filteredAlerts = alerts;

        renderNotification();
        renderTable();
    } catch(error) {
        console.error("Error loading alerts:", error);
    }
}

function renderTable() {
    const totalPages = Math.max(
        1,
        Math.ceil(filteredAlerts.length / recordsPerPage)
    );

    if(currentPage > totalPages) {
        currentPage = totalPages;
    }

    const start = (currentPage - 1) * recordsPerPage;
    const end = start + recordsPerPage;
    const pageData = filteredAlerts.slice(start, end);

    const html = pageData.map(item => {
        let severity = "Medium";
        let severityClass = "severity-medium";

        if(item.confidence >= 90) {
            severity = "Critical";
            severityClass = "severity-critical";
        } else if(item.confidence >= 70) {
            severity = "High";
            severityClass = "severity-high";
        }

        const fallbackRemark = item.prediction === "NORMAL" 
            ? "System operating normally within standard thresholds." 
            : `${severity}: resource usage deviation (${item.confidence}% confidence). Review recommended.`;
        const remark = item.remark || fallbackRemark;

        return `
            <tr>
                <td>${item.server_name}</td>
                <td><span class="badge-danger">${item.prediction}</span></td>
                <td>${item.confidence}%</td>
                <td><span class="${severityClass}">${severity}</span></td>
                <td>${(item.possible_causes || []).join(", ")}</td>
                <td style="text-align: left; font-size: 13px; color: #475569;">${remark}</td>
            </tr>
        `;
    }).join("");

    document.getElementById("alertsTableBody").innerHTML = html;
    document.getElementById("alertPageNumber").innerText =
        `Page ${currentPage} of ${totalPages}`;

    document.getElementById("nextAlertBtn").disabled =
        currentPage >= totalPages;
    document.getElementById("prevAlertBtn").disabled =
        currentPage <= 1;
}

function renderNotification() {
    const notification = document.getElementById("alertsNotification");

    notification.classList.remove("notification-warning", "notification-success");

    if(alerts.length > 0) {
        notification.classList.add("notification-warning");
        notification.innerHTML =
            `<i class="fas fa-bell"></i>
             <span>${alerts.length} active alert${alerts.length === 1 ? "" : "s"} need review.</span>`;
        return;
    }

    notification.classList.add("notification-success");
    notification.innerHTML =
        `<i class="fas fa-circle-check"></i>
         <span>No active alerts at the moment.</span>`;
}

document.getElementById("nextAlertBtn").addEventListener("click", () => {
    const totalPages = Math.max(
        1,
        Math.ceil(filteredAlerts.length / recordsPerPage)
    );

    if(currentPage < totalPages) {
        currentPage++;
        renderTable();
    }
});

document.getElementById("prevAlertBtn").addEventListener("click", () => {
    if(currentPage > 1) {
        currentPage--;
        renderTable();
    }
});

loadAlerts();

setInterval(
    loadAlerts,
    3000
);
