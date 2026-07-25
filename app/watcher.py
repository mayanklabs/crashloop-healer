import time
import threading
import docker
from app.metrics import containers_monitored
from app.recovery import recover, last_healthy_image, restart_counts

client = docker.from_env()
POLL_INTERVAL = 5

def _is_unhealthy(container) -> tuple[bool, str]:
    state = container.attrs.get("State", {})
    if state.get("Status") != "running":
        return True, f"status={state.get('Status')}, exit_code={state.get('ExitCode')}"
    if state.get("OOMKilled"):
        return True, "OOMKilled"
    if container.attrs.get("RestartCount", 0) > 0:
        health = state.get("Health", {})
        if health.get("Status") == "unhealthy":
            return True, "healthcheck_unhealthy"
    return False, ""

def _update_healthy_image(container):
    name = container.name
    image = container.attrs.get("Config", {}).get("Image", "")
    if image:
        last_healthy_image[name] = image
        restart_counts.pop(name, None)

def watch_loop():
    while True:
        try:
            containers = client.containers.list(all=True)
            containers_monitored.set(len(containers))

            for container in containers:
                if (
                    container.name.startswith("crashloop-healer")
                    or container.name.startswith("prometheus")
                    or container.name.startswith("grafana")
                ):
                    continue

                unhealthy, reason = _is_unhealthy(container)
                if unhealthy:
                    recover(container.name)
                else:
                    _update_healthy_image(container)

        except Exception as e:
            print(f"[watcher] error: {e}")

        time.sleep(POLL_INTERVAL)

def start_watcher():
    thread = threading.Thread(target=watch_loop, daemon=True)
    thread.start()
    return thread