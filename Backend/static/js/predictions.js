let predictions = [];
let filteredPredictions = [];

let currentPage = 1;
const recordsPerPage = 10;

async function loadPredictions() {

    try {

        const response =
            await fetch("/all-predictions");

        predictions =
            await response.json();

        const filter =
            document.getElementById(
                "predictionFilter"
            ).value;

        if(filter === "all"){

            filteredPredictions =
                predictions;
        }
        else{

            filteredPredictions =
                predictions.filter(
                    p =>
                    p.prediction === filter
                );
        }

        renderTable();

    } catch(error){

        console.error(
            "Error loading predictions:",
            error
        );
    }
}

function renderTable() {

    const start =
        (currentPage - 1) *
        recordsPerPage;

    const end =
        start +
        recordsPerPage;

    const pageData =
        filteredPredictions.slice(
            start,
            end
        );

    let html = "";

    pageData.forEach(item => {

        let badge = "";

        if(item.prediction === "ANOMALY"){

            badge =
            `<span class="badge-danger">
                ANOMALY
             </span>`;
        }
        else{

            badge =
            `<span class="badge-success">
                NORMAL
             </span>`;
        }

        html += `
        <tr>

            <td>${item.server_name}</td>

            <td>${badge}</td>

            <td>${item.confidence}%</td>

            <td>${item.cpu_usage_percent}%</td>

            <td>${item.memory_usage_percent}%</td>

            <td>${item.disk_usage_percent}%</td>

            <td>${item.timestamp}</td>

        </tr>
        `;
    });

    document.getElementById(
        "predictionTableBody"
    ).innerHTML = html;

    document.getElementById(
        "predictionPageNumber"
    ).innerText = currentPage;
}


document
.getElementById("predictionFilter")
.addEventListener("change", e => {

    const value =
        e.target.value;

    if(value === "all"){

        filteredPredictions =
            predictions;
    }
    else{

        filteredPredictions =
            predictions.filter(
                p =>
                p.prediction === value
            );
    }

    currentPage = 1;

    renderTable();
});


document
.getElementById("nextPredictionBtn")
.addEventListener("click", () => {

    if(
        currentPage <
        Math.ceil(
            filteredPredictions.length /
            recordsPerPage
        )
    ){

        currentPage++;

        renderTable();
    }
});


document
.getElementById("prevPredictionBtn")
.addEventListener("click", () => {

    if(currentPage > 1){

        currentPage--;

        renderTable();
    }
});


loadPredictions();

setInterval(
    loadPredictions,
    3000
);