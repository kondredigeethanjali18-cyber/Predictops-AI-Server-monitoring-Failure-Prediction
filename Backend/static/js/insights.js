async function loadInsights() {
    try {
        const response = await fetch("/ai-insights");
        const data = await response.json();

        // 1. Top Cards
        const topRiskEl = document.getElementById("topRisk");
        if (topRiskEl) {
            topRiskEl.innerHTML = `<i class="fas fa-server" style="color: #64748b; margin-right: 6px;"></i> ${data.top_risk || "None"}`;
        }

        const highestCpuEl = document.getElementById("highestCPU");
        if (highestCpuEl) {
            const cpuVal = data.highest_cpu_val !== undefined ? `${data.highest_cpu_val}%` : "";
            highestCpuEl.innerHTML = `<i class="fas fa-microchip" style="color: #64748b; margin-right: 6px;"></i> ${data.highest_cpu || "None"} <span style="font-size: 16px; color: #dc2626; font-weight: 700;">${cpuVal}</span>`;
        }

        const highestMemEl = document.getElementById("highestMemory");
        if (highestMemEl) {
            const memVal = data.highest_memory_val !== undefined ? `${data.highest_memory_val}%` : "";
            highestMemEl.innerHTML = `<i class="fas fa-memory" style="color: #64748b; margin-right: 6px;"></i> ${data.highest_memory || "None"} <span style="font-size: 16px; color: #8b5cf6; font-weight: 700;">${memVal}</span>`;
        }

        // Subtext and tags
        const topRiskSubtext = document.getElementById("topRiskSubtext");
        if (topRiskSubtext && data.top_risk_confidence) {
            topRiskSubtext.innerText = `Anomaly confidence: ${data.top_risk_confidence}%`;
        }

        const activeAnomaliesCountText = document.getElementById("activeAnomaliesCountText");
        if (activeAnomaliesCountText && data.total_anomalies !== undefined) {
            activeAnomaliesCountText.innerText = `${data.total_anomalies} Active Anomalies Detected`;
        }

        // 2. Risk and Confidence Gauges
        const riskScoreEl = document.getElementById("riskScore");
        if (riskScoreEl) {
            riskScoreEl.innerText = data.risk_score || "96%";
        }

        const riskScoreBar = document.getElementById("riskScoreBar");
        if (riskScoreBar) {
            const numRisk = parseFloat(data.risk_score) || 96;
            riskScoreBar.style.width = `${Math.min(100, numRisk)}%`;
        }

        const predConfEl = document.getElementById("predictionConfidence");
        if (predConfEl) {
            predConfEl.innerText = data.prediction_confidence || "95%";
        }

        const confScoreBar = document.getElementById("confidenceScoreBar");
        if (confScoreBar) {
            const numConf = parseFloat(data.prediction_confidence) || 95;
            confScoreBar.style.width = `${Math.min(100, numConf)}%`;
        }

        // 3. AI Recommendation
        const recEl = document.getElementById("recommendation");
        if (recEl && data.recommendation) {
            recEl.innerHTML = `<i class="fas fa-robot" style="color: #2563eb; margin-right: 6px;"></i> ${data.recommendation}`;
        }

        // Causes Pills
        const causesPillsEl = document.getElementById("causesPills");
        if (causesPillsEl) {
            if (data.top_risk_causes && data.top_risk_causes.length > 0) {
                causesPillsEl.innerHTML = data.top_risk_causes
                    .map(c => `<span class="badge-danger" style="margin-right: 4px; margin-bottom: 4px;"><i class="fas fa-triangle-exclamation"></i> ${c}</span>`)
                    .join("");
            } else {
                causesPillsEl.innerHTML = `<span class="badge-success"><i class="fas fa-circle-check"></i> Standard Telemetry Baseline</span>`;
            }
        }

        // 4. Suggested Actions Checklist
        const actionListEl = document.getElementById("actionList");
        if (actionListEl && data.actions && data.actions.length > 0) {
            actionListEl.innerHTML = data.actions
                .map(action => `
                    <li style="display: flex; align-items: flex-start; gap: 10px; font-size: 13px; color: #334155; line-height: 1.4;">
                        <i class="fas fa-circle-check" style="color: #2563eb; margin-top: 3px; font-size: 14px;"></i>
                        <span>${action}</span>
                    </li>
                `)
                .join("");
        }

    } catch (error) {
        console.error("Error loading insights:", error);
    }
}

// Initial load & 8-second interval
loadInsights();
setInterval(loadInsights, 8000);