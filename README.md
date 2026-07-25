# CrashLoop Healer

> **Never wake up at 2 AM to restart a crashed container again.** 🛌

Your containers crash. We watch. We fix. You sleep.

---

## The Problem (in Plain English)

You're running containers in production. Sometimes they:

- **Crash repeatedly** (crash-loop) — the app has a bug, runs out of memory, or hits a bad request
- **Get OOM-killed** — Linux kills them for using too much RAM
- **Go silent** — nobody notices until customers complain

You end up manually restarting things at 2 AM. That's not sustainable.

---

## What This Does

**CrashLoop Healer** is a tiny watchdog that runs alongside your containers. It:

1. **Watches** every container every 5 seconds
2. **Detects** crash-loops and OOM kills automatically
3. **Fixes** them in two stages:
   - **First:** Restart with exponential backoff (2s → 4s → 8s...)
   - **Then:** If it keeps crashing, **roll back to the last known healthy version**
4. **Shows** you a live dashboard with **MTTR** (Mean Time To Recovery) so you know it's working

No code changes to your app. No agents to install inside containers. Just drop it in.

---

## 🚀 Quick Start (30 seconds)

### Option 1: Try it with the included demo stack

```bash
git clone https://github.com/your-repo/crashloop-healer
cd crashloop-healer
docker compose up -d --build
```

Open **<http://localhost:8000>** — you'll see the dashboard.

### Option 2: Add it to YOUR existing project (recommended)

**Just copy one file.** No, really.

1. Copy `docker-compose.healer.yml` into any project that uses Docker Compose
2. Run it alongside your existing stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.healer.yml up -d
```

That's it. The healer starts monitoring **all containers** in that project automatically.

---

## What You Get

| Feature | What It Means |
|---------|---------------|
| 🟢 **Live Dashboard** | <http://localhost:8000> — see every container's status, restarts, and recovery history |
| 📊 **MTTR Tracking** | Know exactly how long recoveries take on average |
| 🔄 **Auto-Rollback** | After 3 failed restarts, it rolls back to the last working image automatically |
| 📈 **Prometheus + Grafana** | Production-grade metrics at <http://localhost:9090> / <http://localhost:3000> |
| 🐳 **Zero Config** | Works with any Docker Compose project — no YAML editing required |

---

## See It In Action

```bash
# 1. Start your app + healer
docker compose -f docker-compose.yml -f docker-compose.healer.yml up -d

# 2. Open the dashboard
open http://localhost:8000

# 3. Break something (in another terminal)
docker kill your-app-container

# 4. Watch the magic
# → Dashboard shows "Crashed" → "Recovering" → "Running"
# → MTTR updates in real time
# → Full history logged in the table
```

---

## The `docker-compose.healer.yml` You Copy

```yaml
version: '3.8'

services:
  healer:
    image: ghcr.io/your-org/crashloop-healer:latest  # or build locally
    container_name: crashloop-healer
    ports:
      - "8000:8000"
    volumes:
      - healer-data:/app/data
      - /var/run/docker.sock:/var/run/docker.sock   # <-- this lets it watch other containers
    restart: unless-stopped

volumes:
  healer-data:
```

**Two things to note:**

- `Docker socket mount` — lets the healer inspect/restart sibling containers (read-only would work too, but restart needs write)
- `healer-data` volume — persists the SQLite database (recovery history survives restarts)

---

## Dashboard Preview

```
┌───────────────────────────────────────────┐
│ CrashLoop Healer    * Last updated: 14:32 │
├──────────┬──────────┬────────────┬────────┤
│ Running  │ Crashed  │ Recoveries │  MTTR  │
│    5     │    0     │     12     │  2.3s  │
├──────────┴──────────┴────────────┴────────┤
│  Recovery History / Health Timeline       │
├──────────┬────────┬────────┬──────────────┤
│ Container│ Status │Restarts│ Last Failure │
│ api      │ Crashed│   3    │ 14:30:15     │
│ worker   │ Running│   0    │ --           │
│ db       │ Running│   0    │ --           │
└──────────┴────────┴────────┴──────────────┘
```

---

## Why This Exists

Built for the **Cloud Native Hackathon (Pune)** — Problem #1: *"The Silent Crash: Self-Healing Watchdog"*

Requirements we had to meet:

- ✅ Uses a **named Docker product** (Docker Compose)
- ✅ Uses a **CNCF Graduated tool** (Prometheus)
- ✅ Detects both **crash-loops AND OOM kills**
- ✅ **Backoff + rollback** remediation (not just restart)
- ✅ **MTTR** visibly tracked
- ✅ Demo runs in **under 3 minutes**

---

## Contributing

Found a bug? Have an idea? **We'd love your help.**

1. Fork the repo
2. Make your change
3. Open a PR

**Just follow our [Code of Conduct](CODE_OF_CONDUCT.md)** — be kind, be constructive, and we'll review promptly.

---

## Tech Details (if you care)

| Layer | Tech |
| ----- | ---- |
| Backend | Python 3.12 + FastAPI |
| Container Control | Docker SDK (docker-py) |
| Database | SQLite (SQLAlchemy) |
| Metrics | Prometheus (CNCF Graduated) |
| Dashboard | Grafana + custom Jinja2/Bootstrap UI |
| Orchestration | Docker Compose |

**Total codebase:** ~10 Python files, zero build steps, zero external dependencies beyond Docker.

---

## License

MIT — Use it, fork it, improve it. Built for the Cloud Native Community Group Pune × Docker Community Pune hackathon.

---

**Questions?** Open an issue. **Want to help?** Open a PR. **Just want it to work?** Copy `docker-compose.healer.yml` and go. 🎯
