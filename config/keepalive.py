"""Self-ping keep-alive for free-tier Render deployments.

Render spins a free web service down after 15 minutes without inbound HTTP
traffic. GitHub Actions cron alone cannot guarantee that traffic: scheduled
runs are best-effort, can start minutes late under load, and are occasionally
dropped entirely, any of which can outlast the 15-minute idle window.

So the application pings its own health endpoint from a background thread as
the primary keep-alive mechanism; the scheduled GitHub Actions workflow
(`.github/workflows/keep-alive.yml`) remains as a fallback and visibility
check.

Render sets RENDER_EXTERNAL_URL on every web service, so on Render no
configuration is needed. Elsewhere (local development, other hosts) the
thread does not start because the variable is absent. Set
KEEPALIVE_ENABLED=false to opt out explicitly, or KEEPALIVE_INTERVAL=<seconds>
to change the cadence.
"""

import logging
import os
import threading
import time
import urllib.request

logger = logging.getLogger(__name__)

_DEFAULT_INTERVAL = 240  # seconds; comfortably inside the 15-minute window
_MIN_INTERVAL = 60

_started = False
_lock = threading.Lock()


def _loop(interval: int, url: str) -> None:
    while True:
        time.sleep(interval)
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                logger.info("keep-alive ping -> %s", response.status)
        except Exception:
            # A failed ping is not fatal: the next one goes out in
            # `interval` seconds. Log so outages are visible in Render logs.
            logger.warning("keep-alive ping failed", exc_info=True)


def start_keepalive() -> None:
    """Start the background self-ping thread, at most once per process."""
    global _started
    with _lock:
        if _started:
            return
        _started = True

    if os.environ.get("KEEPALIVE_ENABLED", "true").lower() in {"0", "false", "no"}:
        logger.info("keep-alive disabled via KEEPALIVE_ENABLED")
        return

    base_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not base_url:
        logger.info("keep-alive not started: RENDER_EXTERNAL_URL is not set")
        return

    try:
        interval = int(os.environ.get("KEEPALIVE_INTERVAL", _DEFAULT_INTERVAL))
    except ValueError:
        interval = _DEFAULT_INTERVAL
    interval = max(_MIN_INTERVAL, interval)

    url = f"{base_url.rstrip('/')}/health/"
    threading.Thread(target=_loop, args=(interval, url), name="keep-alive", daemon=True).start()
    logger.info("keep-alive started: pinging %s every %ss", url, interval)
