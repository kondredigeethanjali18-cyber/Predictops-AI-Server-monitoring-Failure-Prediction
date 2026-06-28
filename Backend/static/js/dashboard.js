

async function loadDashboard() {

    const response =
        await fetch("/all-predictions");

    const data =
        await response.json();

    let healthy = 0;
    let warning = 0;
    let critical = 0;
    const serverNames = new Set();

    data.forEach(server => {

        serverNames.add(
            server.server_name || "Unknown"
        );

        const cpu =
            server.cpu_usage_percent;

        const memory =
            server.memory_usage_percent;

        if(cpu > 90 || memory > 90){

            critical++;

        }
        else if(cpu > 70 || memory > 80){

            warning++;

        }
        else{

            healthy++;
        }
    });

    document.getElementById(
        "totalServers"
    ).innerText = serverNames.size;

    document.getElementById(
        "totalRecords"
    ).innerText = data.length;

    document.getElementById(
        "healthyServers"
    ).innerText = healthy;

    document.getElementById(
        "warningServers"
    ).innerText = warning;

    document.getElementById(
        "criticalServers"
    ).innerText = critical;

    if(data.length > 0){

       const riskServer =
        data.reduce(
        (max, current) => {

        const currentRisk =
            current.cpu_usage_percent +
            current.memory_usage_percent;

        const maxRisk =
            max.cpu_usage_percent +
            max.memory_usage_percent;

        return currentRisk > maxRisk
            ? current
            : max;
    }
);

     document.getElementById("topRiskServer").innerText =riskServer.server_name;

        document.getElementById(
            "latestPrediction"
        ).innerText =
            data[0].prediction;

        document.getElementById(
            "lastUpdated"
        ).innerText =
            new Date()
            .toLocaleTimeString();
    }

    const anomalies =
        data.filter(
            x => x.prediction === "ANOMALY"
        );

    if(anomalies.length > 0){

    document.getElementById(
        "recentAlerts"
    ).innerHTML =
        anomalies
        .slice(0,3)
        .map(
            a =>
            `<span class="alert-line"><i class="fas fa-circle-exclamation alert-icon alert-icon-danger"></i> ${a.server_name}</span>`
        )
        .join("<br>");
}
    else{

    document.getElementById(
        "recentAlerts"
    ).innerHTML =
        '<span class="alert-line"><i class="fas fa-circle-check alert-icon alert-icon-success"></i> No active alerts</span>';
}
}

loadDashboard();

setInterval(loadDashboard,3000);
