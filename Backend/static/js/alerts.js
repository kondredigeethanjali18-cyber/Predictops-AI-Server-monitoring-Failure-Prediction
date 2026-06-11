async function loadAlerts() {

    const response = await fetch("/all-predictions");

    const predictions = await response.json();

    let html = "";

    predictions.forEach(item => {

        if(item.prediction === "ANOMALY"){

            let severity = "";
            let severityClass = "";

            if(item.confidence >= 90){
                severity = "Critical";
                severityClass = "severity-critical";
            }
            else if(item.confidence >= 70){
                severity = "High";
                severityClass = "severity-high";
            }
            else{
                severity = "Medium";
                severityClass = "severity-medium";
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

                <td>${item.possible_causes.join(", ")}</td>

            </tr>
            `;
        }

    });

    document.getElementById(
        "alertsTableBody"
    ).innerHTML = html;
}

loadAlerts();

setInterval(
    loadAlerts,
    3000
);