async function loadPredictions() {

    const response =
        await fetch("/all-predictions");

    const predictions =
        await response.json();

    let html = "";

    predictions.forEach(item => {

        let predictionBadge = "";

        if(item.prediction === "ANOMALY"){
            predictionBadge =
            `<span class="badge-danger">ANOMALY</span>`;
        }
        else{
            predictionBadge =
            `<span class="badge-success">NORMAL</span>`;
        }

        html += `
        <tr>

            <td>${item.server_name}</td>

            <td>
                ${predictionBadge}
            </td>

            <td>${item.confidence}%</td>

            <td>${item.cpu_usage_percent}%</td>

            <td>${item.memory_usage_percent}%</td>

            <td>${item.disk_usage_percent}%</td>

            <td>${item.timestamp}</td>

        </tr>
        `;
    });

    document.getElementById(
        "predictionTableBody"
    ).innerHTML = html;
}

loadPredictions();

setInterval(
    loadPredictions,
    3000
);