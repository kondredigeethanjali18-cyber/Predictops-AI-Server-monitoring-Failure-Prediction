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

    const topCpuServers =
    [...data]
    .sort(
        (a,b) =>
        b.cpu_usage_percent -
        a.cpu_usage_percent
    )
    .slice(0,5);

const cpuServerNames =
    topCpuServers.map(
        x => x.server_name
    );

const cpuData =
    topCpuServers.map(
        x => x.cpu_usage_percent
    );

const topMemoryServers =
    [...data]
    .sort(
        (a,b) =>
        b.memory_usage_percent -
        a.memory_usage_percent
    )
    .slice(0,5);

const memoryServerNames =
    topMemoryServers.map(
        x => x.server_name
    );

const memoryData =
    topMemoryServers.map(
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
    document.getElementById("cpuChart"),
    {
        type:"bar",
        data:{
            labels:cpuServerNames,
            datasets:[{
                label:"CPU %",
                data:cpuData,

                backgroundColor:
                    cpuData.map(cpu =>
                        cpu > 80
                        ? "#ef4444"
                        : cpu > 60
                        ? "#f59e0b"
                        : "#22c55e"
                    )
            }]
        },
        options:{
            indexAxis:"y",
            responsive:true,
            maintainAspectRatio:false
        }
    }
);

    if(memoryChart){
        memoryChart.destroy();
    }

    memoryChart =
new Chart(
    document.getElementById("memoryChart"),
    {
        type:"bar",
        data:{
            labels:memoryServerNames,
            datasets:[{
                label:"Memory %",
                data:memoryData,

                backgroundColor:
                    memoryData.map(memory =>
                        memory > 85
                        ? "#ef4444"
                        : memory > 70
                        ? "#f59e0b"
                        : "#22c55e"
                    )
            }]
        },
        options:{
            indexAxis:"y",
            responsive:true,
            maintainAspectRatio:false
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
                },
                options:{
                    responsive:true,
                    maintainAspectRatio:false
            }
        }
    );
}

loadAnalytics();

setInterval(
    loadAnalytics,
    5000
);