let eventSource = null;
let lastEventId = 0;
let allEvents = [];

async function fetchInitialData() {
    try {
        const [containersRes, eventsRes] = await Promise.all([
            fetch("/api/containers"),
            fetch("/api/events")
        ]);
        const containers = await containersRes.json();
        const events = await eventsRes.json();
        allEvents = events;
        lastEventId = events.length > 0 ? Math.max(...events.map(e => e.id)) : 0;
        return { containers, events };
    } catch (e) {
        console.error("[dashboard] fetch error:", e);
        return { containers: [], events: [] };
    }
}

function connectEventStream() {
    if (eventSource) {
        eventSource.close();
    }
    eventSource = new EventSource(`/api/events/stream?last_event_id=${lastEventId}`);

    eventSource.onmessage = (event) => {
        try {
            const newEvent = JSON.parse(event.data);
            if (newEvent.id > lastEventId) {
                lastEventId = newEvent.id;
                allEvents.unshift(newEvent);
                prependEvent(newEvent);
                updateStats();
            }
        } catch (e) {
            console.error("[dashboard] SSE parse error:", e);
        }
    };

    eventSource.onerror = (err) => {
        console.error("[dashboard] SSE error, reconnecting in 5s:", err);
        eventSource.close();
        setTimeout(connectEventStream, 5000);
    };
}

function prependEvent(event) {
    const tbody = document.getElementById("eventsBody");
    const emptyState = document.getElementById("emptyState");
    emptyState.classList.add("d-none");

    const isOom = event.status === "oom_killed";
    const row = document.createElement("tr");
    row.style.animationDelay = "0s";
    row.innerHTML = `<td><span class="container-name">${event.container_name}</span></td><td><span class="status-badge ${isOom ? "status-crashed" : "status-crashed"}">${isOom ? "OOM Killed" : "Crash Loop"}</span></td><td><span class="restart-count">${event.restart_count}</span></td><td><span class="timestamp">${formatTime(event.started_at)}</span></td><td><span class="action-badge ${event.action === "rollback" ? "action-rollback" : "action-restart"}">${event.action}</span></td><td><span class="duration">${formatDuration(event.duration_ms)}</span></td><td><button class="btn-recover" onclick="triggerRecovery('${event.container_name}')">Recover</button></td>`;

    tbody.insertBefore(row, tbody.firstChild);
    renderStats(window.currentContainers || [], allEvents);
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
    if (container.status === "Up") {
        return `<span class="status-badge status-running">Running</span>`;
    }
    if (container.oom_killed || container.status === "Exited" || container.restart_count > 0) {
        return `<span class="status-badge status-crashed">Crashed</span>`;
    }
    return `<span class="status-badge status-recovering">Recovering</span>`;
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
        return `<tr style="animation-delay:${i * 0.05}s"><td><span class="container-name">${e.container_name}</span></td><td><span class="status-badge ${isOom ? "status-crashed" : "status-crashed"}">${isOom ? "OOM Killed" : "Crash Loop"}</span></td><td><span class="restart-count">${e.restart_count}</span></td><td><span class="timestamp">${formatTime(e.started_at)}</span></td><td><span class="action-badge ${e.action === "rollback" ? "action-rollback" : "action-restart"}">${e.action}</span></td><td><span class="duration">${formatDuration(e.duration_ms)}</span></td><td><button class="btn-recover" onclick="triggerRecovery('${e.container_name}')">Recover</button></td></tr>`;
    }).join("");
}

function renderStats(containers, events) {
    const running = containers.filter(c => c.status === "Up").length;
    const crashed = containers.filter(c => c.status !== "Up" || c.oom_killed).length;
    const recoveries = allEvents.length;

    let mttr = 0;
    const durations = allEvents.map(e => e.duration_ms).filter(d => d != null);
    if (durations.length > 0) {
        mttr = durations.reduce((a, b) => a + b, 0) / durations.length;
    }

    document.getElementById("statRunning").textContent = running;
    document.getElementById("statCrashed").textContent = crashed;
    document.getElementById("statRecoveries").textContent = recoveries;
    document.getElementById("statMttr").textContent = mttr < 1000 ? `${Math.round(mttr)}ms` : `${(mttr / 1000).toFixed(1)}s`;
    document.getElementById("updateTime").textContent = new Date().toLocaleTimeString();
}

async function fetchContainers() {
    try {
        const res = await fetch("/api/containers");
        window.currentContainers = await res.json();
        renderStats(window.currentContainers, allEvents);
    } catch (e) {
        console.error("[dashboard] containers fetch error:", e);
    }
}

async function refresh() {
    await fetchContainers();
}

async function triggerRecovery(containerName) {
    const btn = document.activeElement;
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

async function init() {
    const { containers, events } = await fetchInitialData();
    window.currentContainers = containers;
    renderStats(containers, events);
    renderEvents(events);
    connectEventStream();
}

init();
