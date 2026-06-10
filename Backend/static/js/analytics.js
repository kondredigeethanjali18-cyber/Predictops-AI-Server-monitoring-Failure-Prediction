let cpuChart;
let memoryChart;
let predictionChart;

async function loadAnalytics() {

    const response =
        await fetch(
            "/all-predictions"
        );

    const data =
        await response.json();

    const serverNames =
        data.map(
            x => x.server_name
        );

    const cpuData =
        data.map(
            x => x.cpu_usage_percent
        );

    const memoryData =
        data.map(
            x => x.memory_usage_percent
        );

    let normalCount = 0;
    let anomalyCount = 0;

    data.forEach(item => {

        if(item.prediction === "NORMAL"){

            normalCount++;

        } else {

            anomalyCount++;
        }
    });

    if(cpuChart){
        cpuChart.destroy();
    }

    cpuChart =
        new Chart(
            document.getElementById(
                "cpuChart"
            ),
            {
                type:"bar",
                data:{
                    labels:serverNames,
                    datasets:[{
                        label:"CPU %",
                        data:cpuData
                    }]
                }
            }
        );

    if(memoryChart){
        memoryChart.destroy();
    }

    memoryChart =
        new Chart(
            document.getElementById(
                "memoryChart"
            ),
            {
                type:"bar",
                data:{
                    labels:serverNames,
                    datasets:[{
                        label:"Memory %",
                        data:memoryData
                    }]
                }
            }
        );

    if(predictionChart){
        predictionChart.destroy();
    }

    predictionChart =
        new Chart(
            document.getElementById(
                "predictionChart"
            ),
            {
                type:"pie",
                data:{
                    labels:[
                        "NORMAL",
                        "ANOMALY"
                    ],
                    datasets:[{
                        data:[
                            normalCount,
                            anomalyCount
                        ]
                    }]
                }
            }
        );
}

loadAnalytics();

setInterval(
    loadAnalytics,
    5000
);