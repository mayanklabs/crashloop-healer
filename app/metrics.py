from prometheus_client import Counter, Gauge, Histogram

container_restarts_total = Counter(
    "container_restarts_total",
    "Total number of container restarts performed",
    ["container_name", "action"],
)

container_failures_total = Counter(
    "container_failures_total",
    "Total number of container failures detected",
    ["container_name", "status"],
)

recovery_duration_seconds = Histogram(
    "recovery_duration_seconds",
    "Time taken to recover a container",
    ["container_name", "action"],
    buckets=[0.5, 1, 2, 5, 10, 20, 30, 60],
)

containers_monitored = Gauge(
    "containers_monitored", "Number of containers currently being monitored"
)
