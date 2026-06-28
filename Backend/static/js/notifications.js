async function loadNotifications() {

    const countEl =
        document.getElementById("notificationCount");

    const panelEl =
        document.getElementById("notificationPanel");

    if(!countEl || !panelEl){
        return;
    }

    try {

        const response =
            await fetch("/all-server-predictions");

        const predictions =
            await response.json();

        const anomalies =
            predictions.filter(
                item =>
                item.prediction === "ANOMALY"
            );

        document.getElementById(
            "notificationCount"
        ).innerText =
            anomalies.length;

        if(anomalies.length === 0){
            panelEl.innerHTML =
                '<div class="notification-empty"><i class="fas fa-circle-check"></i> No active anomaly notifications</div>';

            return;
        }

        const html =
            anomalies
            .slice(0, 8)
            .map(item => {
                const confidence =
                    item.confidence !== undefined
                    ? `${item.confidence}%`
                    : "N/A";

                const notificationTime =
                    formatNotificationTime(
                        item.timestamp
                    );

                return `
            <div class="notification-item">

                <i class="fas fa-triangle-exclamation alert-icon"></i>

                <div>

                    <strong>${item.server_name}</strong>

                    <br>

                    Confidence:
                    ${confidence}

                    <div class="notification-time">
                        <i class="fas fa-clock"></i>
                        ${notificationTime}
                    </div>

                </div>

            </div>
            `;
            })
            .join("");

        panelEl.innerHTML = html;

    } catch(error) {

        console.error(
            "Notification Error:",
            error
        );

        panelEl.innerHTML =
            '<div class="notification-empty">Unable to load notifications</div>';
    }
}

function formatNotificationTime(timestamp) {

    if(!timestamp){
        return "Time unavailable";
    }

    const date =
        new Date(timestamp);

    if(Number.isNaN(date.getTime())){
        return timestamp;
    }

    return date.toLocaleString(
        [],
        {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit"
        }
    );
}

const notificationBell =
    document.getElementById("notificationBell");

if(notificationBell){

notificationBell
.addEventListener("click", event => {

    event.stopPropagation();

    const panel =
        document.getElementById(
            "notificationPanel"
        );

    panel.style.display =
        panel.style.display === "block"
        ? "none"
        : "block";
});

document.addEventListener("click", event => {

    const panel =
        document.getElementById("notificationPanel");

    const widget =
        event.target.closest(".notification-widget");

    if(panel && !widget){
        panel.style.display = "none";
    }
});

loadNotifications();

setInterval(
    loadNotifications,
    5000
);
}
