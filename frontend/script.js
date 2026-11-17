
const API_BASE = "http://127.0.0.1:8000";

const state = {
    fileId: null,
    fileName: null,
    columns: [],
    numericColumns: [],
    categoricalColumns: [],
    currentPage: 1,
    totalPages: 1,
    pageSize: 10,
    cleaned: false
};


// ======================================
// 1. COMMON HELPERS
// ======================================

const $ = (id) => document.getElementById(id);


function showMessage(message, type = "info") {
    const box = $("statusMessage");

    box.textContent = message;
    box.className = `status-message ${type}`;

    window.scrollTo({ top: 0, behavior: "smooth" });

    setTimeout(() => {
        box.classList.add("hidden");
    }, 5000);
}


async function apiRequest(endpoint, options = {}) {
    const response = await fetch(`${API_BASE}${endpoint}`, options);

    if (!response.ok) {
        let message = "Something went wrong.";

        try {
            const error = await response.json();
            message = error.detail || error.message || message;
        } catch {
            message = response.statusText || message;
        }

        throw new Error(message);
    }

    return response;
}


function requireDataset() {
    if (!state.fileId) {
        showMessage("Please upload a dataset first.", "error");
        return false;
    }

    return true;
}


function formatNumber(value) {
    if (value === null || value === undefined) {
        return "—";
    }

    if (typeof value === "number") {
        return value.toLocaleString();
    }

    return value;
}


function renderTable(headElement, bodyElement, columns, rows) {
    headElement.innerHTML = "";
    bodyElement.innerHTML = "";

    if (!columns || columns.length === 0) {
        bodyElement.innerHTML =
            '<tr><td class="empty-state">No data available.</td></tr>';
        return;
    }

    const headerRow = document.createElement("tr");

    columns.forEach(column => {
        const th = document.createElement("th");
        th.textContent = column;
        headerRow.appendChild(th);
    });

    headElement.appendChild(headerRow);

    if (!rows || rows.length === 0) {
        bodyElement.innerHTML =
            `<tr><td colspan="${columns.length}" class="empty-state">
                No records found.
            </td></tr>`;
        return;
    }

    rows.forEach(row => {
        const tr = document.createElement("tr");

        columns.forEach(column => {
            const td = document.createElement("td");

            const value = Array.isArray(row)
                ? row[columns.indexOf(column)]
                : row[column];

            td.textContent = value ?? "—";

            tr.appendChild(td);
        });

        bodyElement.appendChild(tr);
    });
}


function populateSelect(elementId, columns, firstLabel = "Select column") {
    const select = $(elementId);

    select.innerHTML = "";

    const firstOption = document.createElement("option");
    firstOption.value = "";
    firstOption.textContent = firstLabel;

    select.appendChild(firstOption);

    columns.forEach(column => {
        const option = document.createElement("option");

        option.value = column;
        option.textContent = column;

        select.appendChild(option);
    });
}


// ======================================
// 2. NAVIGATION
// ======================================

const pageTitles = {
    overview: "Overview",
    preview: "Data Preview",
    quality: "Data Quality",
    cleaning: "Data Cleaning",
    visualization: "Visualization",
    statistics: "Statistics",
    about: "About Data Lens"
};


function openPage(pageName) {
    document.body.classList.toggle("about-active", pageName === "about");

    document.querySelectorAll(".page").forEach(page => {
        page.classList.remove("active");
    });

    document.querySelectorAll(".nav-link").forEach(button => {
        button.classList.remove("active");
    });

    $(pageName).classList.add("active");

    const activeButton = document.querySelector(
        `.nav-link[data-page="${pageName}"]`
    );

    if (activeButton) {
        activeButton.classList.add("active");
    }

    $("pageTitle").textContent = pageTitles[pageName];
    $("breadcrumbPage").textContent = pageTitles[pageName];

    $("sidebar").classList.remove("open");

    if (!state.fileId) {
        return;
    }

    if (pageName === "preview") {
        loadPreview();
    }

    if (pageName === "quality") {
        loadQuality();
    }
}


document.querySelectorAll(".nav-link").forEach(button => {
    button.addEventListener("click", () => {
        openPage(button.dataset.page);
    });
});


document.querySelectorAll("[data-go]").forEach(button => {
    button.addEventListener("click", () => {
        openPage(button.dataset.go);
    });
});


$("mobileMenu").addEventListener("click", () => {
    $("sidebar").classList.toggle("open");
});


// ======================================
// 3. DATASET UPLOAD
// ======================================

const fileInput = $("fileInput");
const uploadBox = $("uploadBox");


$("browseButton").addEventListener("click", () => {
    fileInput.click();
});


uploadBox.addEventListener("click", event => {
    if (
        event.target.id !== "browseButton" &&
        event.target.tagName !== "BUTTON"
    ) {
        fileInput.click();
    }
});


uploadBox.addEventListener("dragover", event => {
    event.preventDefault();
    uploadBox.classList.add("dragover");
});


uploadBox.addEventListener("dragleave", () => {
    uploadBox.classList.remove("dragover");
});


uploadBox.addEventListener("drop", event => {
    event.preventDefault();

    uploadBox.classList.remove("dragover");

    const file = event.dataTransfer.files[0];

    if (file) {
        uploadDataset(file);
    }
});


fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];

    if (file) {
        uploadDataset(file);
    }
});


async function uploadDataset(file) {
    const allowedExtensions = [".csv", ".xlsx", ".xls"];

    const extension = file.name.substring(
        file.name.lastIndexOf(".")
    ).toLowerCase();

    if (!allowedExtensions.includes(extension)) {
        showMessage("Please upload a CSV or Excel file.", "error");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
        showMessage("Uploading and processing your dataset...", "info");

        const response = await apiRequest("/api/upload", {
            method: "POST",
            body: formData
        });

        const result = await response.json();

        state.fileId = result.file_id;
        state.fileName = result.file_name || file.name;
        state.columns = result.columns || [];

        state.numericColumns = result.numeric_columns || [];

        state.categoricalColumns = state.columns.filter(
            column => !state.numericColumns.includes(column)
        );

        $("fileName").textContent = state.fileName;
        $("currentFileName").textContent = state.fileName;

        $("datasetInfo").classList.remove("hidden");

        populateSelect("columnSelect", state.columns, "All columns");
        populateSelect("cleanColumn", state.columns);
        populateSelect("statisticsColumn", state.numericColumns);

        updateChartControls();

        state.currentPage = 1;

        await loadOverview();

        showMessage("Dataset uploaded successfully!", "success");

        openPage("overview");

    } catch (error) {
        showMessage(error.message, "error");
    }
}


// ======================================
// 4. DATASET OVERVIEW
// ======================================

async function loadOverview() {
    if (!requireDataset()) return;

    try {
        const response = await apiRequest(
            `/api/overview?file_id=${encodeURIComponent(state.fileId)}`
        );

        const data = await response.json();

        $("totalRows").textContent = formatNumber(data.total_rows);
        $("totalColumns").textContent = formatNumber(data.total_columns);
        $("totalEntries").textContent = formatNumber(data.total_entries);
        $("totalMissing").textContent = formatNumber(data.total_missing_values);
        $("totalDuplicates").textContent = formatNumber(data.total_duplicates);

        const columns = data.column_data_types || {};

        $("columnInformation").innerHTML = "";

        Object.entries(columns).forEach(([name, type]) => {
            const item = document.createElement("div");
            item.className = "column-item";

            const strong = document.createElement("strong");
            strong.textContent = name;

            const badge = document.createElement("span");
            badge.className = "type-tag";
            badge.textContent = type;

            item.append(strong, badge);

            $("columnInformation").appendChild(item);
        });

        const preview = await apiRequest(
            `/api/preview?file_id=${encodeURIComponent(state.fileId)}&page=1&page_size=5`
        );

        const previewData = await preview.json();

        renderTable(
            $("overviewTableHead"),
            $("overviewTableBody"),
            previewData.columns || [],
            previewData.records || []
        );

    } catch (error) {
        showMessage(error.message, "error");
    }
}


// ======================================
// 5. DATA PREVIEW
// ======================================

async function loadPreview() {
    if (!requireDataset()) return;

    try {
        const search = $("searchInput").value;
        const pageSize = $("rowLimit").value;
        const selectedColumn = $("columnSelect").value;

        const params = new URLSearchParams({
            file_id: state.fileId,
            page: state.currentPage,
            page_size: pageSize,
            search: search
        });

        if (selectedColumn) {
            params.append("column", selectedColumn);
        }

        const response = await apiRequest(
            `/api/preview?${params.toString()}`
        );

        const data = await response.json();

        renderTable(
            $("previewTableHead"),
            $("previewTableBody"),
            data.columns || [],
            data.records || []
        );

        state.totalPages = data.total_pages || 1;

        $("pageInformation").textContent =
            `Page ${state.currentPage} of ${state.totalPages}`;

        $("previousPage").disabled = state.currentPage <= 1;
        $("nextPage").disabled = state.currentPage >= state.totalPages;

    } catch (error) {
        showMessage(error.message, "error");
    }
}


$("applyPreview").addEventListener("click", () => {
    state.currentPage = 1;
    loadPreview();
});


$("searchInput").addEventListener("keydown", event => {
    if (event.key === "Enter") {
        state.currentPage = 1;
        loadPreview();
    }
});


$("previousPage").addEventListener("click", () => {
    if (state.currentPage > 1) {
        state.currentPage--;
        loadPreview();
    }
});


$("nextPage").addEventListener("click", () => {
    if (state.currentPage < state.totalPages) {
        state.currentPage++;
        loadPreview();
    }
});


// ======================================
// 6. DATA QUALITY
// ======================================

async function loadQuality() {
    if (!requireDataset()) return;

    try {
        const response = await apiRequest(
            `/api/quality?file_id=${encodeURIComponent(state.fileId)}`
        );

        const data = await response.json();

        $("completenessScore").textContent =
            `${data.completeness ?? 0}%`;

        $("missingPercentage").textContent =
            `${data.missing_percentage ?? 0}%`;

        $("duplicatePercentage").textContent =
            `${data.duplicate_percentage ?? 0}%`;

        $("completenessBar").style.width =
            `${Math.min(100, Math.max(0, data.completeness ?? 0))}%`;

        const missing = data.missing_values_by_column || {};
        const missingPercent = data.missing_percentage_by_column || {};
        const unique = data.unique_values_by_column || {};
        const types = data.column_data_types || {};

        const columns = Object.keys(types);

        const body = $("qualityTableBody");
        body.innerHTML = "";

        columns.forEach(column => {
            const tr = document.createElement("tr");

            [
                column,
                types[column],
                formatNumber(missing[column] ?? 0),
                `${missingPercent[column] ?? 0}%`,
                formatNumber(unique[column] ?? 0)
            ].forEach(value => {
                const td = document.createElement("td");
                td.textContent = value;
                tr.appendChild(td);
            });

            body.appendChild(tr);
        });

    } catch (error) {
        showMessage(error.message, "error");
    }
}


$("refreshQuality").addEventListener("click", loadQuality);


// ======================================
// 7. DATA CLEANING
// ======================================

$("cleaningForm").addEventListener("submit", async event => {
    event.preventDefault();

    if (!requireDataset()) return;

    const operation = $("cleanOperation").value;
    const column = $("cleanColumn").value;
    const value = $("cleanValue").value;

    const payload = {
        file_id: state.fileId,
        operation: operation,
        column: column || null,
        value: value
    };

    try {
        const response = await apiRequest("/api/clean", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        state.cleaned = true;

        displayCleaningSummary(result.summary || {});

        showMessage("Cleaning operation completed!", "success");

        await loadOverview();
        await loadQuality();

    } catch (error) {
        showMessage(error.message, "error");
    }
});


function displayCleaningSummary(summary) {
    const labels = {
        original_rows: "Original rows",
        cleaned_rows: "Cleaned rows",
        removed_rows: "Rows removed",
        original_columns: "Original columns",
        cleaned_columns: "Cleaned columns",
        removed_columns: "Columns removed",
        original_missing_values: "Original missing values",
        remaining_missing_values: "Remaining missing values",
        original_duplicates: "Original duplicates",
        remaining_duplicates: "Remaining duplicates"
    };

    const container = $("cleaningSummary");
    container.innerHTML = "";

    Object.entries(labels).forEach(([key, label]) => {
        const row = document.createElement("div");
        row.className = "summary-row";

        const name = document.createElement("span");
        name.textContent = label;

        const value = document.createElement("strong");
        value.textContent = formatNumber(summary[key]);

        row.append(name, value);
        container.appendChild(row);
    });
}


// ======================================
// 8. DOWNLOAD CLEANED DATA
// ======================================

async function downloadCleanedFile(format) {
    if (!requireDataset()) return;

    if (!state.cleaned) {
        showMessage("Please clean your dataset before downloading.", "error");
        return;
    }

    try {
        const response = await apiRequest(
            `/api/export?file_id=${encodeURIComponent(state.fileId)}&format=${format}`
        );

        const blob = await response.blob();

        const url = URL.createObjectURL(blob);

        const link = document.createElement("a");

        link.href = url;
        link.download = `cleaned_data.${format}`;

        document.body.appendChild(link);
        link.click();
        link.remove();

        URL.revokeObjectURL(url);

        showMessage("Download started!", "success");

    } catch (error) {
        showMessage(error.message, "error");
    }
}


$("downloadCsv").addEventListener("click", () => {
    downloadCleanedFile("csv");
});


$("downloadExcel").addEventListener("click", () => {
    downloadCleanedFile("xlsx");
});


// ======================================
// 9. DYNAMIC CHART CONTROLS
// ======================================

function updateChartControls() {

    const chartType = $("chartType").value;

    const xGroup = $("chartXGroup");
    const yGroup = $("chartYGroup");

    const xLabel = $("chartXLabel");
    const yLabel = $("chartYLabel");

    // Reset visibility
    xGroup.style.display = "block";
    yGroup.style.display = "block";

    // Default labels
    xLabel.textContent = "X-axis column";
    yLabel.textContent = "Y-axis numeric column";

    // Histogram: one numeric column
    if (chartType === "histogram") {

        xGroup.style.display = "block";
        yGroup.style.display = "none";

        xLabel.textContent = "Select numeric column";

        populateSelect("chartX", state.numericColumns);
    }

    // Box plot: one numeric column
    else if (chartType === "box") {

        xGroup.style.display = "block";
        yGroup.style.display = "none";

        xLabel.textContent = "Select numeric column";

        populateSelect("chartX", state.numericColumns);
    }

    // Pie chart: one categorical column
    else if (chartType === "pie") {

        xGroup.style.display = "block";
        yGroup.style.display = "none";

        xLabel.textContent = "Select category column";

        populateSelect("chartX", state.categoricalColumns);
    }

    // Heatmap: no column selection
    else if (chartType === "heatmap") {

        xGroup.style.display = "none";
        yGroup.style.display = "none";
    }

    // Scatter plot: both columns numeric
    else if (chartType === "scatter") {

        xLabel.textContent = "X-axis numeric column";
        yLabel.textContent = "Y-axis numeric column";

        populateSelect("chartX", state.numericColumns);
        populateSelect("chartY", state.numericColumns);
    }

    // Horizontal bar chart
    else if (chartType === "horizontal_bar") {

        xLabel.textContent = "Category column";
        yLabel.textContent = "Numeric value column";

        populateSelect("chartX", state.categoricalColumns);
        populateSelect("chartY", state.numericColumns);
    }

    // Bar, line and area charts
    else {

        xLabel.textContent = "X-axis column";
        yLabel.textContent = "Y-axis numeric column";

        populateSelect("chartX", state.columns);
        populateSelect("chartY", state.numericColumns);
    }
}


// Listen for chart type changes
$("chartType").addEventListener("change", updateChartControls);


// ======================================
// 10. DATA VISUALIZATION
// ======================================

$("visualizationForm").addEventListener("submit", async event => {
    event.preventDefault();

    if (!requireDataset()) return;

    const chartType = $("chartType").value;

    const payload = {
        file_id: state.fileId,
        chart_type: chartType,
        x_column: $("chartX").value || null,
        y_column: $("chartY").value || null
    };

    // Single-column charts use x_column
    if (["histogram", "box", "pie"].includes(chartType)) {
        payload.y_column = null;
    }

    // Heatmap does not require columns
    if (chartType === "heatmap") {
        payload.x_column = null;
        payload.y_column = null;
    }

    try {
        showMessage("Generating visualization...", "info");

        const response = await apiRequest("/api/visualize", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        if (!response.headers.get("content-type")?.includes("image/png")) {
            throw new Error("The server did not return a valid chart image.");
        }

        const imageBlob = await response.blob();

        if (imageBlob.size === 0) {
            throw new Error("The generated chart image is empty.");
        }

        const imageUrl = URL.createObjectURL(imageBlob);

        const output = $("chartOutput");
        output.innerHTML = "";

        const image = document.createElement("img");
        image.src = imageUrl;
        image.alt = "Generated data visualization";

        output.appendChild(image);

        showMessage("Chart generated successfully!", "success");

    } catch (error) {
        showMessage(error.message, "error");
    }
});


// ======================================
// 11. STATISTICAL ANALYSIS
// ======================================

$("runStatistics").addEventListener("click", async () => {
    if (!requireDataset()) return;

    const column = $("statisticsColumn").value;

    if (!column) {
        showMessage("Please select a numeric column.", "error");
        return;
    }

    try {
        const params = new URLSearchParams({
            file_id: state.fileId,
            column: column
        });

        const response = await apiRequest(
            `/api/statistics?${params.toString()}`
        );

        const data = await response.json();

        const results = {
            statMean: data.mean,
            statMedian: data.median,
            statMode: data.mode,
            statMin: data.minimum,
            statMax: data.maximum,
            statStd: data.standard_deviation,
            statVariance: data.variance,
            statRange: data.range,
            statSkewness: data.skewness,
            statKurtosis: data.kurtosis,
            statQ1: data.Q1,
            statQ3: data.Q3
        };

        Object.entries(results).forEach(([id, value]) => {
            $(id).textContent = Array.isArray(value)
                ? value.join(", ")
                : formatNumber(value);
        });

        showMessage("Statistical analysis completed!", "success");

    } catch (error) {
        showMessage(error.message, "error");
    }
});


// ======================================
// 12. REMOVE DATASET FROM INTERFACE
// ======================================

$("removeDataset").addEventListener("click", () => {
    state.fileId = null;
    state.fileName = null;
    state.columns = [];
    state.numericColumns = [];
    state.categoricalColumns = [];
    state.currentPage = 1;
    state.totalPages = 1;
    state.cleaned = false;

    $("datasetInfo").classList.add("hidden");
    $("fileName").textContent = "";
    fileInput.value = "";

    $("totalRows").textContent = "—";
    $("totalColumns").textContent = "—";
    $("totalEntries").textContent = "—";
    $("totalMissing").textContent = "—";
    $("totalDuplicates").textContent = "—";

    $("columnInformation").innerHTML =
        '<p class="empty-state">No dataset loaded.</p>';

    $("cleaningSummary").innerHTML =
        '<p class="empty-state">No cleaning operations performed yet.</p>';

    showMessage(
        "Dataset removed from the current interface.",
        "info"
    );
});


// ======================================
// 13. INITIALIZATION
// ======================================

document.addEventListener("DOMContentLoaded", () => {
    console.log("Data Lens V2 frontend initialized.");

    $("sidebar").classList.remove("open");

    updateChartControls();
});
