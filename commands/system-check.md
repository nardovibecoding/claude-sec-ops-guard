---
name: system-check
description: Full system health check — Mac + VPS processes, MCP servers, cron jobs, disk, memory, cookies, heartbeat. One command to see everything.
---

Run a comprehensive system health check across Mac and VPS.

## Check these in parallel:

### VPS (ssh $VPS_USER@$VPS_HOST):
1. **Bot processes**: `pgrep -fa "run_bot|admin_bot"` — configured bots alive?
2. **systemd services**: check configured systemd services are active
3. **MCP health**: curl health endpoints on configured MCP service ports
4. **Heartbeat**: check configured heartbeat file — age < 60s?
5. **Disk**: `df -h /` — usage %
6. **Memory**: `free -m` — usage
7. **Docker**: `docker ps` — any configured containers running?
8. **Cookie age**: check configured cookie file — how old?
9. **Today's cron jobs**: check which daily jobs ran (grep today's date in each log)
10. **Recent errors**: `grep -i "error\|traceback" /tmp/start_all.log | tail -5`

### Mac:
1. **Voice daemon**: `pgrep -f voice_daemon`
2. **Recording indicator**: `pgrep -f recording_indicator`
3. **Sync script**: check `/tmp/claude-memory-sync.log` last run time
4. **Local services**: curl health endpoints on any configured local service ports

## Output format:
Present as a clean status table with ✅/❌ for each item.
