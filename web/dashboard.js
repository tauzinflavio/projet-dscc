const statusLine = document.getElementById("status");
const rows = document.getElementById("rows");
const total = document.getElementById("total");
const latestClass = document.getElementById("latest-class");
const latestFile = document.getElementById("latest-file");
const averageConfidence = document.getElementById("average-confidence");
const averageLatency = document.getElementById("average-latency");
const percent = new Intl.NumberFormat("fr-FR", {style: "percent", maximumFractionDigits: 1});
const clock = new Intl.DateTimeFormat("fr-FR", {dateStyle: "short", timeStyle: "medium"});
let chart;

function cell(row, content, className) {
  const item = row.insertCell();
  if (className) item.className = className;
  if (typeof content === "string") item.textContent = content;
  else item.append(content);
  return item;
}

function render(data) {
  const counts = [0, 0, 0];
  const fragment = document.createDocumentFragment();
  for (const item of data) {
    if (item.prediction >= 1 && item.prediction <= 3) counts[item.prediction - 1]++;
    const row = document.createElement("tr");
    cell(row, item.fileName, "file-name");
    cell(row, clock.format(new Date(item.processedAt)));
    const pill = document.createElement("span");
    pill.className = "class-pill class-" + item.prediction;
    pill.textContent = "Cultivar " + item.prediction;
    cell(row, pill);
    const confidence = document.createElement("span");
    confidence.className = "confidence";
    const value = document.createElement("span");
    value.textContent = percent.format(item.confidence);
    const bar = document.createElement("span");
    bar.className = "confidence-bar";
    const fill = document.createElement("span");
    fill.style.width = Math.max(0, Math.min(100, item.confidence * 100)) + "%";
    bar.append(fill);
    confidence.append(value, bar);
    cell(row, confidence);
    cell(row, item.durationMs.toFixed(2) + " ms");
    fragment.append(row);
  }
  rows.replaceChildren(fragment);
  if (!data.length) {
    const row = document.createElement("tr");
    cell(row, "Aucune analyse pour le moment.", "empty").colSpan = 5;
    rows.append(row);
  }
  total.textContent = String(data.length);
  latestClass.textContent = data.length ? "Cultivar " + data[0].prediction : "—";
  latestFile.textContent = data.length ? data[0].fileName : "En attente d’une analyse";
  averageConfidence.textContent = data.length ? percent.format(data.reduce((sum, item) => sum + item.confidence, 0) / data.length) : "—";
  averageLatency.textContent = data.length ? (data.reduce((sum, item) => sum + item.durationMs, 0) / data.length).toFixed(2) + " ms" : "—";
  if (typeof Chart === "undefined") return;
  if (!chart) {
    chart = new Chart(document.getElementById("chart"), {
      type: "bar",
      data: {
        labels: ["Cultivar 1", "Cultivar 2", "Cultivar 3"],
        datasets: [{data: counts, backgroundColor: ["#9d5366", "#b18268", "#698c77"], borderRadius: 6, maxBarThickness: 80}]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {legend: {display: false}},
        scales: {
          x: {grid: {display: false}, ticks: {color: "#7a8790"}},
          y: {beginAtZero: true, ticks: {stepSize: 1, precision: 0, color: "#9ba6ad"}, grid: {color: "#edf1f3"}, border: {display: false}}
        }
      }
    });
  } else {
    chart.data.datasets[0].data = counts;
    chart.update();
  }
}

async function refresh() {
  try {
    const response = await fetch(window.RECENT_URL, {cache: "no-store", signal: AbortSignal.timeout(15000)});
    if (!response.ok) throw new Error("HTTP " + response.status);
    const data = await response.json();
    render(data);
    statusLine.textContent = "Mis à jour à " + new Date().toLocaleTimeString("fr-FR");
  } catch {
    statusLine.textContent = "Données momentanément indisponibles. Nouvelle tentative dans 30 secondes.";
  } finally {
    window.setTimeout(refresh, 30000);
  }
}
refresh();
