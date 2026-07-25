# Learnings

* css-dark-theme-visibility: Table body cells (tbody td) in dark theme must have explicit `color: var(--fg)` or they inherit browser default black text, making them invisible on dark backgrounds. Headers (thead th) also need explicit bright color override since Bootstrap defaults them to muted.
* docker-sdk-run-kwargs: Docker SDK's `containers.run()` uses `nano_cpus` and `mem_limit` not `cpus`/`mem_limit`. Also need to filter out `None` values and `image` key from run_args.
* docker-restart-count: `container.restart()` does NOT increment Docker's `RestartCount` - must recreate container with `remove(force=True)` + `run()` to increment restart count properly.
* in-memory-tracking: Module-level dicts (`last_healthy_image`, `restart_counts`) in `recovery.py` need to be imported where used. The watcher clears `restart_counts` when container is healthy.
* crash-target-design: For demo, crash-target should run healthy long enough (30s+) for watcher to record `last_healthy_image` before first crash, then crash repeatedly to demonstrate backoff → rollback escalation.
