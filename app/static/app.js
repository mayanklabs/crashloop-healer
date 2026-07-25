async function fetchData() {
    try {
        const [containersRes, eventsRes] = await Promise.all([
            fetch("/api/containers"),
            fetch("/api/events")
        ]);
        const containers = await containersRes.json();
        const events = await eventsRes.json();
        return { containers, events };
    } catch (e) {
        console.error("[dashboard] fetch error:", e);
        return { containers: [], events: [] };
    }
}

function formatTime(iso) {
    if (!iso) return "--";
    const date = new Date(iso);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function formatDuration(ms) {
    if (ms == null) return "--";
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
}

function getStatusBadge(container) {
    if (container.status === "running") {
        return `<span class="status-badge status-running">Running</span>`;
    }
    if (container.oom_killed || container.status === "exited" || container.restart_count > 0) {
        return `<span class="status-badge status-crashed">Crashed</span>`;
    }
    return `<span class="status-badge status-recovering">Recovering</span>`;
}

function renderStats(containers, events) {
    const running = containers.filter(c => c.status === "running").length;
    const crashed = containers.filter(c => c.status !== "running" || c.oom_killed).length;
    const recoveries = events.length;

    let mttr = 0;
    if (events.length > 0) {
        const durations = events.map(e => e.duration_ms).filter(d => d != null);
        mttr = durations.reduce((a, b) => a + b, 0) / durations.length;
    }

    document.getElementById("statRunning").textContent = running;
    document.getElementById("statCrashed").textContent = crashed;
    document.getElementById("statRecoveries").textContent = recoveries;
    document.getElementById("statMttr").textContent = mttr < 1000 ? `${Math.round(mttr)}ms` : `${(mttr / 1000).toFixed(1)}s`;
}

function renderEvents(events) {
    const tbody = document.getElementById("eventsBody");
    const emptyState = document.getElementById("emptyState");

    if (events.length === 0) {
        tbody.innerHTML = "";
        emptyState.classList.remove("d-none");
        return;
    }

    emptyState.classList.add("d-none");

    tbody.innerHTML = events.map((e, i) => {
        const isOom = e.status === "oom_killed";
        return `<tr style="animation-delay:${i*0.05}s"><td><span class="container-name">${e.container_name}</span></td><td><span class="status-badge ${isOom?"status-crashed":"status-crashed"}">${isOom?"OOM Killed":"Crash Loop"}</span></td><td><span class="restart-count">${e.restart_count}</span></td><td><span class="timestamp">${formatTime(e.started_at)}</span></td><td><span class="action-badge ${e.action==="rollback"?"action-rollback":"action-restart"}">${e.action}</span></td><td><span class="duration">${formatDuration(e.duration_ms)}</span></td><td><button class="btn-recover" onclick="triggerRecovery('${e.container_name}')">Recover</button></td></tr>`;
    }).join("");
}

async function triggerRecovery(containerName) {
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = "Recovering...";

    try {
        const res = await fetch(`/api/recover/${containerName}`, { method: "POST" });
        if (!res.ok) throw new Error(await res.text());
        await refresh();
    } catch (e) {
        alert("Recovery failed: " + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = "Recover";
    }
}

async function refresh() {
    const { containers, events } = await fetchData();
    renderStats(containers, events);
    renderEvents(events);
    document.getElementById("updateTime").textContent = new Date().toLocaleTimeString();
}

refresh();
setInterval(refresh, 5000);
