let cpuChart;
let memoryChart;
let utilizationChart;
let throughputChart;
let predictionChart;
let statusDistributionChart;

async function loadAnalytics() {
    try {
        const response = await fetch("/all-predictions");
        const data = await response.json();

        const serversResponse = await fetch("/all-servers");
        const serversData = await serversResponse.json();

        // 1. CPU Chart Data
        const cpuServers = [...serversData].sort(
            (a, b) => b.cpu_usage_percent - a.cpu_usage_percent
        );
        const cpuServerNames = cpuServers.map(x => x.server_name);
        const cpuData = cpuServers.map(x => x.cpu_usage_percent);

        // 2. Memory Chart Data
        const topMemoryServers = [...data]
            .sort((a, b) => b.memory_usage_percent - a.memory_usage_percent)
            .slice(0, 5);
        const memoryServerNames = topMemoryServers.map(x => x.server_name);
        const memoryData = topMemoryServers.map(x => x.memory_usage_percent);

        // 3. Historical Anomaly Counts (All predictions)
        let normalCount = 0;
        let anomalyCount = 0;
        data.forEach(item => {
            if (item.prediction === "NORMAL") {
                normalCount++;
            } else {
                anomalyCount++;
            }
        });

        document.getElementById("totalPredictions").innerText = data.length;
        document.getElementById("normalPredictions").innerText = normalCount;
        document.getElementById("anomalyPredictions").innerText = anomalyCount;

        // 4. Latest Status by Server Data (Latest entry per server)
        const latestByServer = {};
        data.forEach(item => {
            if (!latestByServer[item.server_name]) {
                latestByServer[item.server_name] = item;
            }
        });
        const uniqueServers = Object.values(latestByServer);

        const utilizationLabels = uniqueServers.map(s => s.server_name);
        const utilizationCpuData = uniqueServers.map(s => s.cpu_usage_percent);
        const utilizationMemData = uniqueServers.map(s => s.memory_usage_percent);

        const throughputLabels = uniqueServers.map(s => s.server_name);
        const throughputData = uniqueServers.map(s => s.network_throughput || 0);

        const serverHealthyCount = Object.values(latestByServer).filter(s => s.prediction === "NORMAL").length;
        const serverAnomalyCount = Object.values(latestByServer).filter(s => s.prediction === "ANOMALY").length;

        // --- DRAW CHARTS ---

        // 1. CPU Chart (Horizontal Bar)
        if (cpuChart) {
            cpuChart.data.labels = cpuServerNames;
            cpuChart.data.datasets[0].data = cpuData;
            cpuChart.data.datasets[0].backgroundColor = cpuData.map(cpu =>
                cpu > 80 ? "#ef4444" : cpu > 60 ? "#f59e0b" : "#22c55e"
            );
            cpuChart.update();
        } else {
            cpuChart = new Chart(document.getElementById("cpuChart"), {
                type: "bar",
                data: {
                    labels: cpuServerNames,
                    datasets: [{
                        label: "CPU %",
                        data: cpuData,
                        backgroundColor: cpuData.map(cpu =>
                            cpu > 80 ? "#ef4444" : cpu > 60 ? "#f59e0b" : "#22c55e"
                        )
                    }]
                },
                options: {
                    indexAxis: "y",
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            beginAtZero: true,
                            max: 100,
                            title: {
                                display: true,
                                text: "CPU utilization (%)"
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: "Server name"
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        }

        // 2. Memory Chart (Horizontal Bar)
        if (memoryChart) {
            memoryChart.data.labels = memoryServerNames;
            memoryChart.data.datasets[0].data = memoryData;
            memoryChart.data.datasets[0].backgroundColor = memoryData.map(memory =>
                memory > 85 ? "#ef4444" : memory > 70 ? "#f59e0b" : "#22c55e"
            );
            memoryChart.update();
        } else {
            memoryChart = new Chart(document.getElementById("memoryChart"), {
                type: "bar",
                data: {
                    labels: memoryServerNames,
                    datasets: [{
                        label: "Memory %",
                        data: memoryData,
                        backgroundColor: memoryData.map(memory =>
                            memory > 85 ? "#ef4444" : memory > 70 ? "#f59e0b" : "#22c55e"
                        )
                    }]
                },
                options: {
                    indexAxis: "y",
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            beginAtZero: true,
                            max: 100,
                            title: {
                                display: true,
                                text: "Memory utilization (%)"
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: "Server name"
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        }

        // 3. Server Utilization (CPU vs Memory side-by-side)
        if (utilizationChart) {
            utilizationChart.data.labels = utilizationLabels;
            utilizationChart.data.datasets[0].data = utilizationCpuData;
            utilizationChart.data.datasets[1].data = utilizationMemData;
            utilizationChart.update();
        } else {
            utilizationChart = new Chart(document.getElementById("utilizationChart"), {
                type: "bar",
                data: {
                    labels: utilizationLabels,
                    datasets: [
                        {
                            label: "CPU Usage %",
                            data: utilizationCpuData,
                            backgroundColor: "rgba(59, 130, 246, 0.8)",
                            borderColor: "rgb(59, 130, 246)",
                            borderWidth: 1,
                            borderRadius: 4
                        },
                        {
                            label: "Memory Usage %",
                            data: utilizationMemData,
                            backgroundColor: "rgba(168, 85, 247, 0.8)",
                            borderColor: "rgb(168, 85, 247)",
                            borderWidth: 1,
                            borderRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            title: {
                                display: true,
                                text: "Usage (%)"
                            }
                        }
                    }
                }
            });
        }

        // 4. Network Throughput Chart
        if (throughputChart) {
            throughputChart.data.labels = throughputLabels;
            throughputChart.data.datasets[0].data = throughputData;
            throughputChart.update();
        } else {
            throughputChart = new Chart(document.getElementById("throughputChart"), {
                type: "bar",
                data: {
                    labels: throughputLabels,
                    datasets: [
                        {
                            label: "Throughput (MB/s)",
                            data: throughputData,
                            backgroundColor: "rgba(244, 63, 94, 0.8)",
                            borderColor: "rgb(244, 63, 94)",
                            borderWidth: 1,
                            borderRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: "Throughput (MB/s)"
                            }
                        }
                    }
                }
            });
        }

        // 5. Historical Anomaly Distribution (Pie Chart)
        if (predictionChart) {
            predictionChart.data.datasets[0].data = [normalCount, anomalyCount];
            predictionChart.update();
        } else {
            predictionChart = new Chart(document.getElementById("predictionChart"), {
                type: "pie",
                data: {
                    labels: ["NORMAL", "ANOMALY"],
                    datasets: [{
                        data: [normalCount, anomalyCount],
                        backgroundColor: ["#22c55e", "#ef4444"]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: "bottom"
                        }
                    }
                }
            });
        }

        // 6. Current Server Status Distribution (Doughnut Chart)
        if (statusDistributionChart) {
            statusDistributionChart.data.datasets[0].data = [serverHealthyCount, serverAnomalyCount];
            statusDistributionChart.update();
        } else {
            statusDistributionChart = new Chart(document.getElementById("statusDistributionChart"), {
                type: "doughnut",
                data: {
                    labels: ["Healthy (NORMAL)", "Anomalous (ANOMALY)"],
                    datasets: [{
                        data: [serverHealthyCount, serverAnomalyCount],
                        backgroundColor: [
                            "rgba(16, 185, 129, 0.8)",
                            "rgba(239, 68, 68, 0.8)"
                        ],
                        borderColor: [
                            "rgb(16, 185, 129)",
                            "rgb(239, 68, 68)"
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: "bottom"
                        }
                    }
                }
            });
        }

    } catch (error) {
        console.error("Error loading analytics:", error);
    }
}

loadAnalytics();
setInterval(loadAnalytics, 5000);
