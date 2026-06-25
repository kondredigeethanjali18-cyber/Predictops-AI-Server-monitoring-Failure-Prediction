async function loadNotifications() {

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

        let html = "";

        anomalies.forEach(item => {

            html += `
            <div class="notification-item">

                <i class="fas fa-triangle-exclamation alert-icon"></i>

                <div>

                    <strong>${item.server_name}</strong>

                    <br>

                    Confidence:
                    ${item.confidence}%

                </div>

            </div>
            `;
        });

        document.getElementById(
            "notificationPanel"
        ).innerHTML = html;

    } catch(error) {

        console.error(
            "Notification Error:",
            error
        );
    }
}

document
.getElementById("notificationBell")
.addEventListener("click", () => {

    const panel =
        document.getElementById(
            "notificationPanel"
        );

    panel.style.display =
        panel.style.display === "block"
        ? "none"
        : "block";
});

loadNotifications();

setInterval(
    loadNotifications,
    5000
);

