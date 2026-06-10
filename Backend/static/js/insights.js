async function loadInsights(){

    const response =
        await fetch(
            "/ai-insights"
        );

    const data =
        await response.json();

    document.getElementById(
        "topRisk"
    ).innerText =
        data.top_risk;

    document.getElementById(
        "highestCPU"
    ).innerText =
        data.highest_cpu;

    document.getElementById(
        "highestMemory"
    ).innerText =
        data.highest_memory;
}

loadInsights();

setInterval(
    loadInsights,
    3000
);