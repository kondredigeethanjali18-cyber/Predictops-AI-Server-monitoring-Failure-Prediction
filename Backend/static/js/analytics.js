// PredictOps AI - Telemetry & Infrastructure Analytics Controller
// Dynamically renders Chart.js visualizations including dynamic Pie & Doughnut charts

let cpuChart = null;
let memoryChart = null;
let utilizationChart = null;
let throughputChart = null;
let predictionChart = null;
let statusDistributionChart = null;

const ANALYTICS_REFRESH_INTERVAL = 8;
let remainingSeconds = ANALYTICS_REFRESH_INTERVAL;
let countdownTimer = null;
let lastSyncDate = new Date();
let isFetchingAnalytics = false;

// Custom Chart.js Plugin for Dynamic Center Text on the Doughnut Chart
const doughnutCenterTextPlugin = {
    id: "doughnutCenterText",
    beforeDraw: function(chart) {
        if (chart.config.type !== "doughnut") return;
        const { ctx } = chart;
        ctx.save();

        const dataset = chart.data.datasets[0];
        const data = dataset ? dataset.data : [];
        const healthy = data[0] || 0;
        const warning = data[1] || 0;
        const critical = data[2] || 0;
        const total = healthy + warning + critical;
        const score = total > 0 ? (((healthy + (warning * 0.5)) / total) * 100).toFixed(1) : "100.0";
        const scoreNum = parseFloat(score);
        const scoreColor = scoreNum >= 90 ? "#10b981" : scoreNum >= 75 ? "#f59e0b" : "#ef4444";

        const centerX = (chart.chartArea.left + chart.chartArea.right) / 2;
        const centerY = (chart.chartArea.top + chart.chartArea.bottom) / 2;

        ctx.textAlign = "center";
        ctx.textBaseline = "middle";

        // Draw Score Number
        ctx.font = "800 22px 'Segoe UI', system-ui, sans-serif";
        ctx.fillStyle = scoreColor;
        ctx.fillText(`${score}%`, centerX, centerY - 8);

        // Draw Subtitle
        ctx.font = "700 10px 'Segoe UI', system-ui, sans-serif";
        ctx.fillStyle = "#64748b";
        ctx.fillText("FLEET HEALTH", centerX, centerY + 12);

        ctx.restore();
    }
};

async function loadAnalytics() {
    if (isFetchingAnalytics) return;
    isFetchingAnalytics = true;

    try {
        const [predRes, serversRes] = await Promise.all([
            fetch("/all-predictions"),
            fetch("/all-servers")
        ]);

        const predictionsData = predRes.ok ? await predRes.json() : [];
        const serversData = serversRes.ok ? await serversRes.json() : [];

        // 1. Process Historical Predictions Spectrum
        let normalCount = 0;
        let anomalyCount = 0;

        predictionsData.forEach(item => {
            if (item.prediction === "NORMAL") {
                normalCount++;
            } else {
                anomalyCount++;
            }
        });

        const totalPredictionsEl = document.getElementById("totalPredictions");
        if (totalPredictionsEl) totalPredictionsEl.innerText = predictionsData.length;

        const normalPredictionsEl = document.getElementById("normalPredictions");
        if (normalPredictionsEl) normalPredictionsEl.innerText = normalCount;

        const anomalyPredictionsEl = document.getElementById("anomalyPredictions");
        if (anomalyPredictionsEl) anomalyPredictionsEl.innerText = anomalyCount;

        // 2. Map Latest Prediction per Server
        const latestPredByServer = {};
        predictionsData.forEach(item => {
            if (!latestPredByServer[item.server_name]) {
                latestPredByServer[item.server_name] = item;
            }
        });

        // 3. Build Unified Server List with Latest Telemetry
        const serverMap = {};
        (serversData || []).forEach(s => {
            serverMap[s.server_name] = { ...s };
        });
        Object.keys(latestPredByServer).forEach(sname => {
            if (!serverMap[sname]) {
                serverMap[sname] = { ...latestPredByServer[sname] };
            }
        });
        const activeServers = Object.values(serverMap);

        // 4. Calculate Dynamic Tri-State Status for Fleet Status Distribution
        let healthyCount = 0;
        let warningCount = 0;
        let criticalCount = 0;

        activeServers.forEach(s => {
            const sPred = latestPredByServer[s.server_name];
            const isAnomaly = sPred && sPred.prediction === "ANOMALY";
            const cpu = Number(s.cpu_usage_percent) || 0;
            const mem = Number(s.memory_usage_percent) || 0;
            const disk = Number(s.disk_usage_percent) || (sPred && sPred.disk_usage_percent !== undefined ? Number(sPred.disk_usage_percent) : 0);

            if (isAnomaly || cpu > 85 || mem > 85 || disk > 85) {
                criticalCount++;
            } else if (cpu > 70 || mem > 75 || disk > 75) {
                warningCount++;
            } else {
                healthyCount++;
            }
        });

        // --- RENDER DYNAMIC CHARTS ---

        // Chart 1: CPU Utilization Across All Servers (Sorted Descending)
        const sortedCpuServers = [...activeServers].sort(
            (a, b) => (Number(b.cpu_usage_percent) || 0) - (Number(a.cpu_usage_percent) || 0)
        );
        const cpuLabels = sortedCpuServers.map(s => s.server_name);
        const cpuValues = sortedCpuServers.map(s => Number(s.cpu_usage_percent) || 0);
        const cpuColors = cpuValues.map(cpu => cpu > 80 ? "#ef4444" : cpu > 60 ? "#f59e0b" : "#22c55e");

        renderCpuChart(cpuLabels, cpuValues, cpuColors);

        // Chart 2: Top 5 Memory Utilization Servers
        const topMemServers = [...activeServers]
            .sort((a, b) => (Number(b.memory_usage_percent) || 0) - (Number(a.memory_usage_percent) || 0))
            .slice(0, 5);
        const memLabels = topMemServers.map(s => s.server_name);
        const memValues = topMemServers.map(s => Number(s.memory_usage_percent) || 0);
        const memColors = memValues.map(mem => mem > 85 ? "#ef4444" : mem > 70 ? "#f59e0b" : "#22c55e");

        renderMemoryChart(memLabels, memValues, memColors);

        // Chart 3: Server Resource Allocation (CPU vs Memory)
        const sortedByServerName = [...activeServers].sort((a, b) => a.server_name.localeCompare(b.server_name));
        const utilLabels = sortedByServerName.map(s => s.server_name);
        const utilCpu = sortedByServerName.map(s => Number(s.cpu_usage_percent) || 0);
        const utilMem = sortedByServerName.map(s => Number(s.memory_usage_percent) || 0);

        renderUtilizationChart(utilLabels, utilCpu, utilMem);

        // Chart 4: Network Throughput per Server (Inbound RX & Outbound TX in MB/s)
        const tpLabels = sortedByServerName.map(s => s.server_name);
        const rxValues = sortedByServerName.map(s => {
            if (s.network_received_mb !== undefined && s.network_received_mb !== null) {
                return Math.round(Number(s.network_received_mb) * 100) / 100;
            }
            const pred = latestPredByServer[s.server_name];
            if (pred && pred.network_throughput) {
                const total = Number(pred.network_throughput) > 100000 ? Number(pred.network_throughput) / (1024 * 1024) : Number(pred.network_throughput);
                return Math.round((total * 0.6) * 100) / 100;
            }
            return 0;
        });

        const txValues = sortedByServerName.map(s => {
            if (s.network_sent_mb !== undefined && s.network_sent_mb !== null) {
                return Math.round(Number(s.network_sent_mb) * 100) / 100;
            }
            const pred = latestPredByServer[s.server_name];
            if (pred && pred.network_throughput) {
                const total = Number(pred.network_throughput) > 100000 ? Number(pred.network_throughput) / (1024 * 1024) : Number(pred.network_throughput);
                return Math.round((total * 0.4) * 100) / 100;
            }
            return 0;
        });

        renderThroughputChart(tpLabels, rxValues, txValues);

        // Chart 5: Historical Anomaly Distribution (Dynamic Pie Chart with Live % and Animation)
        renderHistoricalPieChart(normalCount, anomalyCount);

        // Chart 6: Current Server Status Distribution (Dynamic Tri-State Donet Chart with Center Health Score)
        renderStatusDistributionChart(healthyCount, warningCount, criticalCount);

        // Update Synced IST Timestamp & Reset Countdown
        lastSyncDate = new Date();
        remainingSeconds = ANALYTICS_REFRESH_INTERVAL;
        renderAnalyticsSyncTime();

    } catch (error) {
        console.error("Error loading analytics data:", error);
    } finally {
        isFetchingAnalytics = false;
    }
}

// -------------------------------------------------------------
// Chart Renderers
// -------------------------------------------------------------

function renderHistoricalPieChart(normalCount, anomalyCount) {
    const ctx = document.getElementById("predictionChart");
    if (!ctx) return;

    const total = normalCount + anomalyCount;
    const normalPct = total > 0 ? ((normalCount / total) * 100).toFixed(1) : "100.0";
    const anomalyPct = total > 0 ? ((anomalyCount / total) * 100).toFixed(1) : "0.0";

    const pieLabels = [`Normal (${normalPct}%)`, `Anomaly (${anomalyPct}%)`];
    const pieData = [normalCount, anomalyCount];
    const pieColors = ["#10b981", "#ef4444"];

    if (predictionChart) {
        predictionChart.data.labels = pieLabels;
        predictionChart.data.datasets[0].data = pieData;
        predictionChart.data.datasets[0].backgroundColor = pieColors;
        predictionChart.update();
    } else {
        predictionChart = new Chart(ctx, {
            type: "pie",
            data: {
                labels: pieLabels,
                datasets: [{
                    data: pieData,
                    backgroundColor: pieColors,
                    borderColor: "#ffffff",
                    borderWidth: 2,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 500,
                    easing: "easeOutQuart"
                },
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            boxWidth: 12,
                            padding: 14,
                            font: {
                                size: 11.5,
                                weight: "700"
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const idx = context.dataIndex;
                                const val = context.raw || 0;
                                const pct = total > 0 ? ((val / total) * 100).toFixed(1) : "0.0";
                                const label = idx === 0 ? "Normal Predictions" : "Anomaly Detections";
                                return ` ${label}: ${val} (${pct}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
}

function renderStatusDistributionChart(healthyCount, warningCount, criticalCount) {
    const ctx = document.getElementById("statusDistributionChart");
    if (!ctx) return;

    const total = healthyCount + warningCount + criticalCount;
    const hPct = total > 0 ? ((healthyCount / total) * 100).toFixed(1) : "100.0";
    const wPct = total > 0 ? ((warningCount / total) * 100).toFixed(1) : "0.0";
    const cPct = total > 0 ? ((criticalCount / total) * 100).toFixed(1) : "0.0";

    const statusLabels = [`Healthy (${hPct}%)`, `Warning (${wPct}%)`, `Critical (${cPct}%)`];
    const statusData = [healthyCount, warningCount, criticalCount];
    const statusColors = ["#10b981", "#f59e0b", "#ef4444"];

    if (statusDistributionChart) {
        statusDistributionChart.data.labels = statusLabels;
        statusDistributionChart.data.datasets[0].data = statusData;
        statusDistributionChart.data.datasets[0].backgroundColor = statusColors;
        statusDistributionChart.update();
    } else {
        statusDistributionChart = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: statusLabels,
                datasets: [{
                    data: statusData,
                    backgroundColor: statusColors,
                    borderColor: "#ffffff",
                    borderWidth: 2,
                    hoverOffset: 8
                }]
            },
            plugins: [doughnutCenterTextPlugin],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "62%",
                animation: {
                    duration: 500,
                    easing: "easeOutQuart"
                },
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            boxWidth: 12,
                            padding: 14,
                            font: {
                                size: 11.5,
                                weight: "700"
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const idx = context.dataIndex;
                                const val = context.raw || 0;
                                const pct = total > 0 ? ((val / total) * 100).toFixed(1) : "0.0";
                                const labelNames = ["Healthy Nodes", "Warning / Elevated", "Critical / At Risk"];
                                return ` ${labelNames[idx]}: ${val} Nodes (${pct}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
}

function renderCpuChart(labels, values, colors) {
    const ctx = document.getElementById("cpuChart");
    if (!ctx) return;

    if (cpuChart) {
        cpuChart.data.labels = labels;
        cpuChart.data.datasets[0].data = values;
        cpuChart.data.datasets[0].backgroundColor = colors;
        cpuChart.update();
    } else {
        cpuChart = new Chart(ctx, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: "CPU %",
                    data: values,
                    backgroundColor: colors,
                    borderRadius: 4
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
                        title: { display: true, text: "CPU Utilization (%)" }
                    },
                    y: {
                        title: { display: true, text: "Server" }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }
}

function renderMemoryChart(labels, values, colors) {
    const ctx = document.getElementById("memoryChart");
    if (!ctx) return;

    if (memoryChart) {
        memoryChart.data.labels = labels;
        memoryChart.data.datasets[0].data = values;
        memoryChart.data.datasets[0].backgroundColor = colors;
        memoryChart.update();
    } else {
        memoryChart = new Chart(ctx, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: "Memory %",
                    data: values,
                    backgroundColor: colors,
                    borderRadius: 4
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
                        title: { display: true, text: "Memory Utilization (%)" }
                    },
                    y: {
                        title: { display: true, text: "Server" }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }
}

function renderUtilizationChart(labels, cpuData, memData) {
    const ctx = document.getElementById("utilizationChart");
    if (!ctx) return;

    if (utilizationChart) {
        utilizationChart.data.labels = labels;
        utilizationChart.data.datasets[0].data = cpuData;
        utilizationChart.data.datasets[1].data = memData;
        utilizationChart.update();
    } else {
        utilizationChart = new Chart(ctx, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "CPU Usage %",
                        data: cpuData,
                        backgroundColor: "rgba(59, 130, 246, 0.85)",
                        borderColor: "rgb(59, 130, 246)",
                        borderWidth: 1,
                        borderRadius: 4
                    },
                    {
                        label: "Memory Usage %",
                        data: memData,
                        backgroundColor: "rgba(168, 85, 247, 0.85)",
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
                        title: { display: true, text: "Usage (%)" }
                    }
                }
            }
        });
    }
}

function renderThroughputChart(labels, rxData, txData) {
    const ctx = document.getElementById("throughputChart");
    if (!ctx) return;

    if (throughputChart) {
        throughputChart.data.labels = labels;
        throughputChart.data.datasets[0].data = rxData;
        throughputChart.data.datasets[1].data = txData;
        throughputChart.update();
    } else {
        throughputChart = new Chart(ctx, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Inbound (RX MB/s)",
                        data: rxData,
                        backgroundColor: "rgba(59, 130, 246, 0.85)",
                        borderColor: "rgb(37, 99, 235)",
                        borderWidth: 1,
                        borderRadius: 4
                    },
                    {
                        label: "Outbound (TX MB/s)",
                        data: txData,
                        backgroundColor: "rgba(244, 63, 94, 0.85)",
                        borderColor: "rgb(225, 29, 72)",
                        borderWidth: 1,
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: { display: false }
                    },
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: "Throughput (MB/s)" }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            afterBody: function(items) {
                                const idx = items[0].dataIndex;
                                const rx = Number(rxData[idx]) || 0;
                                const tx = Number(txData[idx]) || 0;
                                const tot = (rx + tx).toFixed(2);
                                return `Total Bandwidth: ${tot} MB/s`;
                            }
                        }
                    }
                }
            }
        });
    }
}

// -------------------------------------------------------------
// Clock & Countdown Synchronization
// -------------------------------------------------------------

function renderAnalyticsSyncTime() {
    const syncTimeEl = document.getElementById("analyticsSyncTime");
    const remainingEl = document.getElementById("analyticsRemainingSecs");

    if (syncTimeEl) {
        syncTimeEl.innerText = lastSyncDate.toLocaleTimeString("en-IN", {
            timeZone: "Asia/Kolkata",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: true
        }) + " (IST)";
    }

    if (remainingEl) {
        remainingEl.innerText = `${remainingSeconds}s`;
    }
}

function startAnalyticsCountdown() {
    if (countdownTimer) clearInterval(countdownTimer);

    countdownTimer = setInterval(() => {
        remainingSeconds--;
        const remainingEl = document.getElementById("analyticsRemainingSecs");
        const badgeEl = document.getElementById("analyticsCountdownBadge");

        if (remainingSeconds <= 0) {
            if (badgeEl) {
                badgeEl.innerHTML = `<i class="fas fa-spinner fa-spin" style="font-size: 10px;"></i> Syncing...`;
            }
            loadAnalytics();
        } else {
            if (badgeEl) {
                badgeEl.innerHTML = `<i class="fas fa-rotate" style="font-size: 10px;"></i> <span id="analyticsRemainingSecs">${remainingSeconds}s</span>`;
            }
        }
    }, 1000);
}

// Initial initialization
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
        loadAnalytics();
        startAnalyticsCountdown();
    });
} else {
    loadAnalytics();
    startAnalyticsCountdown();
}
