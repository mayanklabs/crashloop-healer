import asyncio
import json
from concurrent.futures import ThreadPoolExecutor

import docker
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.database import SessionLocal
from app.models import RecoveryEvent
from app.recovery import recover

router = APIRouter()
client = docker.from_env()
api_client = docker.APIClient()

EXCLUDED_PREFIXES = (
    "crashloop-healer",
    "prometheus",
    "grafana",
    "redis",
    "db",
    "postgres",
    "seed",
    "docker-compose",  # microservices demo - not our app
)


def _inspect_container(cid: str) -> dict:
    """Get detailed container state via inspect."""
    try:
        info = api_client.inspect_container(cid)
        state = info.get("State", {})
        return {
            "restart_count": state.get("RestartCount", 0),
            "oom_killed": state.get("OOMKilled", False),
            "exit_code": state.get("ExitCode"),
            "started_at": state.get("StartedAt"),
            "finished_at": state.get("FinishedAt"),
        }
    except Exception:
        return {
            "restart_count": 0,
            "oom_killed": False,
            "exit_code": None,
            "started_at": None,
            "finished_at": None,
        }


@router.get("/containers")
def list_containers():
    # Fast list all containers
    all_containers = api_client.containers(all=True)

    # Filter to our project containers
    our_containers = []
    for c in all_containers:
        name = c["Names"][0].lstrip("/") if c["Names"] else c["Id"][:12]
        if any(name.startswith(p) for p in EXCLUDED_PREFIXES):
            continue
        our_containers.append(c)

    # Parallel inspect for detailed state (restart_count, oom_killed, etc.)
    details = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
        for cid, detail in zip(
            [c["Id"] for c in our_containers],
            ex.map(_inspect_container, [c["Id"] for c in our_containers]),
        ):
            details[cid[:12]] = detail

    # Build response
    containers = []
    for c in our_containers:
        name = c["Names"][0].lstrip("/") if c["Names"] else c["Id"][:12]
        cid12 = c["Id"][:12]
        state = c.get("State", "")
        status = c.get("Status", "").split(" ")[0]
        d = details.get(cid12, {})

        containers.append({
            "name": name,
            "id": cid12,
            "image": c.get("Image", ""),
            "status": status,
            "restart_count": d.get("restart_count", 0),
            "oom_killed": d.get("oom_killed", False),
            "exit_code": d.get("exit_code"),
            "started_at": d.get("started_at"),
            "finished_at": d.get("finished_at"),
        })
    return containers


@router.get("/events")
def list_events(limit: int = 50):
    db = SessionLocal()
    try:
        events = (
            db
            .query(RecoveryEvent)
            .order_by(RecoveryEvent.started_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": e.id,
                "container_name": e.container_name,
                "status": e.status,
                "reason": e.reason,
                "restart_count": e.restart_count,
                "action": e.action,
                "image_before": e.image_before,
                "image_after": e.image_after,
                "started_at": e.started_at.isoformat() + "Z" if e.started_at else None,
                "finished_at": e.finished_at.isoformat() + "Z" if e.finished_at else None,
                "duration_ms": e.duration_ms,
            }
            for e in events
        ]
    finally:
        db.close()


async def event_generator(last_event_id: int = 0):
    """SSE generator yielding new recovery events as they arrive."""
    db = SessionLocal()
    try:
        while True:
            events = (
                db
                .query(RecoveryEvent)
                .filter(RecoveryEvent.id > last_event_id)
                .order_by(RecoveryEvent.started_at.asc())
                .all()
            )
            for e in events:
                last_event_id = e.id
                data = {
                    "id": e.id,
                    "container_name": e.container_name,
                    "status": e.status,
                    "reason": e.reason,
                    "restart_count": e.restart_count,
                    "action": e.action,
                    "image_before": e.image_before,
                    "image_after": e.image_after,
                    "started_at": e.started_at.isoformat() + "Z" if e.started_at else None,
                    "finished_at": e.finished_at.isoformat() + "Z" if e.finished_at else None,
                    "duration_ms": e.duration_ms,
                }
                yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(1)
    finally:
        db.close()


@router.get("/events/stream")
async def stream_events(last_event_id: int = 0):
    """Server-Sent Events endpoint for real-time recovery event updates."""
    return StreamingResponse(
        event_generator(last_event_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/recover/{container_name}")
def trigger_recovery(container_name: str):
    try:
        result = recover(container_name)
        return {"success": True, **result}
    except docker.errors.NotFound:
        raise HTTPException(404, f"Container '{container_name}' not found")
    except Exception as e:
        raise HTTPException(500, str(e))
