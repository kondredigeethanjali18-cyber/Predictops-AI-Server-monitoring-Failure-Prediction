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

    if (data.highest_cpu) {

        document.getElementById(
            "recommendation"
        ).innerText =

        `${data.highest_cpu} is experiencing high CPU utilization.

Investigation recommended.`;

    }
}

loadInsights();

setInterval(
    loadInsights,
    3000
);