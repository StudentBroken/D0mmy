const statusEl = document.getElementById("status");

async function checkConnection() {
  try {
    const res = await fetch("http://localhost:8000/health");
    if (res.ok) {
      statusEl.textContent = "Orchestrator: connected";
      statusEl.style.color = "#7fff7f";
    } else {
      throw new Error();
    }
  } catch {
    statusEl.textContent = "Orchestrator: offline";
    statusEl.style.color = "#ff4444";
  }
}

checkConnection();
