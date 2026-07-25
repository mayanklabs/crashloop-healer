import time

import docker
from sqlalchemy.sql import func

from app.database import SessionLocal
from app.metrics import (
    container_failures_total,
    container_restarts_total,
    recovery_duration_seconds,
)
from app.models import RecoveryEvent

RESTART_THRESHOLD = 3
MAX_BACKOFF = 30

last_healthy_image: dict[str, str] = {}

client = docker.from_env()


def _extract_run_args(inspect: dict) -> dict:
    config = inspect.get("Config", {})
    host_config = inspect.get("HostConfig", {})
    ncpus = host_config.get("NanoCpus")
    mlimit = host_config.get("Memory")
    return {
        "image": config.get("Image"),
        "command": config.get("Cmd"),
        "entrypoint": config.get("Entrypoint"),
        "working_dir": config.get("WorkingDir"),
        "environment": config.get("Env"),
        "ports": host_config.get("PortBindings"),
        "volumes": host_config.get("Binds"),
        "network_mode": host_config.get("NetworkMode"),
        "restart_policy": host_config.get("RestartPolicy"),
        "nano_cpus": ncpus if ncpus and ncpus > 0 else None,
        "mem_limit": mlimit if mlimit and mlimit > 0 else None,
    }


def _recreate_container(
    container_name: str, image: str, inspect: dict, run_args: dict
) -> str:
    labels = inspect.get("Config", {}).get("Labels", {})
    kwargs = {k: v for k, v in run_args.items() if v is not None and k != "image"}
    new_container = client.containers.run(
        image, name=container_name, detach=True, labels=labels, **kwargs
    )
    return new_container.id


def recover(container_name: str) -> dict:
    start = time.time()
    container = client.containers.get(container_name)
    inspect = container.attrs

    state = inspect.get("State", {})
    oom_killed = state.get("OOMKilled", False)
    exit_code = state.get("ExitCode", 0)
    restart_count = inspect.get("RestartCount", 0)

    status = "oom_killed" if oom_killed else "crash_loop"
    reason = (
        f"OOMKilled: {oom_killed}, ExitCode: {exit_code}, RestartCount: {restart_count}"
    )

    image_before = inspect.get("Config", {}).get("Image", "")
    run_args = _extract_run_args(inspect)

    if restart_count < RESTART_THRESHOLD:
        backoff = min(2**restart_count, MAX_BACKOFF)
        time.sleep(backoff)
        container.restart()
        action = "restart"
        image_after = image_before
    else:
        healthy_image = last_healthy_image.get(container_name)
        if healthy_image and healthy_image != image_before:
            container.remove(force=True)
            _recreate_container(container_name, healthy_image, inspect, run_args)
            image_after = healthy_image
            action = "rollback"
        else:
            backoff = min(2**restart_count, MAX_BACKOFF)
            time.sleep(backoff)
            container.restart()
            action = "restart"
            image_after = image_before

    duration_ms = int((time.time() - start) * 1000)

    db = SessionLocal()
    try:
        event = RecoveryEvent(
            container_name=container_name,
            status=status,
            reason=reason,
            restart_count=restart_count,
            action=action,
            image_before=image_before,
            image_after=image_after,
            duration_ms=duration_ms,
            finished_at=func.now(),
        )
        db.add(event)
        db.commit()
    finally:
        db.close()

    container_restarts_total.labels(container_name=container_name, action=action).inc()
    container_failures_total.labels(container_name=container_name, status=status).inc()
    recovery_duration_seconds.labels(
        container_name=container_name, action=action
    ).observe(duration_ms / 1000)

    return {
        "container": container_name,
        "action": action,
        "status": status,
        "duration_ms": duration_ms,
        "image_before": image_before,
        "image_after": image_after,
    }
