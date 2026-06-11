async function loadInsights() {

    const response =
        await fetch("/ai-insights");

    const data =
        await response.json();

    document.getElementById(
        "topRisk"
    ).innerText =
        data.top_risk || "No Data";

    document.getElementById(
        "highestCPU"
    ).innerText =
        data.highest_cpu || "No Data";

    document.getElementById(
        "highestMemory"
    ).innerText =
        data.highest_memory || "No Data";

    let recommendation = "System operating normally.";

    if(data.highest_cpu){

        recommendation =
        `${data.highest_cpu} is showing elevated CPU utilization. Investigate running processes and resource allocation.`;

    }

    document.getElementById(
        "recommendation"
    ).innerText =
        recommendation;

    document.getElementById(
        "riskScore"
    ).innerText =
        "96%";

    document.getElementById(
        "predictionConfidence"
    ).innerText =
        "95%";
}

loadInsights();

setInterval(
    loadInsights,
    3000
);