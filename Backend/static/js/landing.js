async function loadStats() {

    const response =
        await fetch("/dashboard-summary");

    const data =
        await response.json();
    
    document.getElementById("serverCount").innerText =data.total || 0;
    document.getElementById("alertCount").innerText =(data.critical || 0) +(data.warning || 0);

}

loadStats();

setInterval(
    loadStats,
    5000
);