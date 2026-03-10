# gunicorn.conf.py – Production WSGI configuration
import os

# ── Server socket ────────────────────────────────────────────────
# Render injects $PORT; fallback to 10000 (Render's default)
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# ── Workers ──────────────────────────────────────────────────────
# Render free tier: 0.5 vCPU → 2 workers max
workers = int(os.environ.get("WEB_CONCURRENCY", 2))
worker_class = "sync"

# ── Timeout ──────────────────────────────────────────────────────
# Give extra time for first-request DB init + chart rendering
timeout = 120
keepalive = 5

# ── Logging ──────────────────────────────────────────────────────
accesslog  = "-"   # stdout → Render log stream
errorlog   = "-"   # stderr → Render log stream
loglevel   = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %(D)sµs'

# ── Reload (dev only, disabled in prod) ──────────────────────────
reload = False

# ── Security ─────────────────────────────────────────────────────
forwarded_allow_ips = "*"   # Render uses a reverse proxy
proxy_protocol = True
proxy_allow_from = "*"
