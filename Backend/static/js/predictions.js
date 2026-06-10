async function loadPredictions() {

    const response =
        await fetch(
            "/all-predictions"
        );

    const predictions =
        await response.json();

    let html = "";

    predictions.forEach(item => {

        html += `
        <tr>
            <td>${item.server_name}</td>
            <td>${item.prediction}</td>
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