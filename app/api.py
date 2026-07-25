import docker
from fastapi import APIRouter, HTTPException

from app.database import SessionLocal
from app.models import RecoveryEvent
from app.recovery import recover

router = APIRouter()
client = docker.from_env()


@router.get("/containers")
def list_containers():
    containers = []
    for c in client.containers.list(all=True):
        state = c.attrs.get("State", {})
        containers.append({
            "name": c.name,
            "id": c.short_id,
            "image": c.image.tags[0] if c.image.tags else c.image.id,
            "status": state.get("Status"),
            "restart_count": state.get("RestartCount", 0),
            "oom_killed": state.get("OOMKilled", False),
            "exit_code": state.get("ExitCode"),
            "started_at": state.get("StartedAt"),
            "finished_at": state.get("FinishedAt"),
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
                "started_at": e.started_at.isoformat() if e.started_at else None,
                "finished_at": e.finished_at.isoformat() if e.finished_at else None,
                "duration_ms": e.duration_ms,
            }
            for e in events
        ]
    finally:
        db.close()


@router.post("/recover/{container_name}")
def trigger_recovery(container_name: str):
    try:
        result = recover(container_name)
        return {"success": True, **result}
    except docker.errors.NotFound:
        raise HTTPException(404, f"Container '{container_name}' not found")
    except Exception as e:
        raise HTTPException(500, str(e))
