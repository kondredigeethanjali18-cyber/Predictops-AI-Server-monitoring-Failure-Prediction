async function loadAlerts() {

    const response =
        await fetch(
            "/all-predictions"
        );

    const predictions =
        await response.json();

    let html = "";

    predictions.forEach(item => {

        if(item.prediction === "ANOMALY"){

            html += `
            <tr>
                <td>${item.server_name}</td>
                <td>${item.prediction}</td>
                <td>${item.confidence}%</td>
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