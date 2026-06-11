let cpuLabels = [];
let cpuValues = [];

let memoryLabels = [];
let memoryValues = [];

let cpuChart;
let memoryChart;

async function loadMetrics() {

    const response =
        await fetch(
            "/latest-metrics"
        );

    const data =
        await response.json();

    const currentTime =
        new Date()
        .toLocaleTimeString();

    cpuLabels.push(
        currentTime
    );

    cpuValues.push(
        data.cpu_usage_percent
    );

    memoryLabels.push(
        currentTime
    );

    memoryValues.push(
        data.memory_usage_percent
    );

    document.getElementById("currentCPU").innerText =data.cpu_usage_percent + "%";

    document.getElementById("currentMemory").innerText =data.memory_usage_percent + "%";

    if(cpuLabels.length > 20){

        cpuLabels.shift();
        cpuValues.shift();

        memoryLabels.shift();
        memoryValues.shift();
    }

    if(!cpuChart){

        cpuChart =
            new Chart(
                document.getElementById(
                    "cpuChart"
                ),
                {
                    type:"line",
                    data:{
                        labels:cpuLabels,
                        datasets:[{
                            label:"CPU %",
                            data:cpuValues,
                            borderColor:"#ef4444",
                            borderwidth:3,
                            fill:false,
                            tension:0.3
                        }]
                    },
                    options:{
                        responsive:true,
                        maintainAspectRatio:false
                    }
                }
            );

    } else {

        cpuChart.update();
    }

    if(!memoryChart){

        memoryChart =
            new Chart(
                document.getElementById(
                    "memoryChart"
                ),
                {
                    type:"line",
                    data:{
                        labels:memoryLabels,
                        datasets:[{
                            label:"Memory %",
                            data:memoryValues,
                            borderColor:"#3b82f6",
                            borderwidth:3,
                            fill:false,
                            tension:0.3
                        }]
                    },
                    options:{
                        responsive:true,
                        maintainAspectRatio:false
                    }
                }
            );

    } else {

        memoryChart.update();
    }
}

loadMetrics();

setInterval(
    loadMetrics,
    3000
);