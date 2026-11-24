const statusLine = document.getElementById("status");
const rows = document.getElementById("rows");
let chart;
const percent = new Intl.NumberFormat("fr-FR", {style: "percent", maximumFractionDigits: 1});
const clock = new Intl.DateTimeFormat("fr-FR", {dateStyle: "short", timeStyle: "medium"});

async function refresh() {
  try {
    const response = await fetch(window.RECENT_URL, {cache: "no-store", signal: AbortSignal.timeout(15000)});
    if (!response.ok) throw new Error(String(response.status));
    const data = await response.json();
    const totals = [0, 0, 0];
    const fragment = document.createDocumentFragment();
    for (const item of data) {
      const row = document.createElement("tr");
      totals[item.prediction - 1]++;
      for (const value of [item.fileName, clock.format(new Date(item.processedAt)), item.prediction,
                           percent.format(item.confidence), item.durationMs.toFixed(2) + " ms"]) {
        const cell = row.insertCell();
        cell.textContent = value;
      }
      fragment.append(row);
    }
    rows.replaceChildren(fragment);
    if (!chart) {
      chart = new Chart(document.getElementById("chart"), {
        type: "bar", data: {labels: ["Cultivar 1", "Cultivar 2", "Cultivar 3"],
          datasets: [{label: "Analyses", data: totals, backgroundColor: ["#673249", "#9b6853", "#557360"]}]},
        options: {maintainAspectRatio: false, plugins: {legend: {display: false}},
          scales: {y: {beginAtZero: true, ticks: {precision: 0}}}}
      });
    } else {
      chart.data.datasets[0].data = totals;
      chart.update();
    }
    statusLine.textContent = data.length ? "Mis à jour à " + new Date().toLocaleTimeString("fr-FR") : "Aucun fichier analysé pour le moment.";
  } catch {
    statusLine.textContent = "Mise à jour impossible. Nouvelle tentative dans 30 secondes.";
  } finally {
    window.setTimeout(refresh, 30000);
  }
}
refresh();
