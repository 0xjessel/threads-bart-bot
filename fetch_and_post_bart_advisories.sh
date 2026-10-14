#!/bin/bash

cd /home/meltedxice/cron_jobs/threads-bart-bot

source venv/bin/activate

STATUS=/home/meltedxice/cron_jobs/threads-bart-bot/.cron_status
WD_ERR=$(mktemp)
echo "========== [$(date +"%Y-%m-%d %H:%M:%S")] ==========" >> /home/meltedxice/cron_jobs/threads-bart-bot/bart_advisories.log
python3 fetch_and_post_bart_advisories.py > "$WD_ERR" 2>&1
__wd_rc=$?
cat "$WD_ERR" >> /home/meltedxice/cron_jobs/threads-bart-bot/bart_advisories.log

# --- cron-watchdog status recorder (added 2026-09-13) ---
# Records exit code + a sanitized one-line error to .cron_status.<suffix> so the
# failure watchdog can track consecutive failures. Additive: does NOT change bot
# logic. Never stores tokens (stderr-only, secrets stripped, truncated to 300ch).
__wd_detail="$(tail -n 20 "$WD_ERR" 2>/dev/null | grep -aEv "^(Traceback|\s*$)" | { grep -aiE "401|429|403|Unauthorized|Forbidden|invalid|expired|rate.?limit|token|Error|failed|exception|refused|timed out" || tail -n 1; } | head -n 1 | tr "\r" " " | cut -c1-300)"
[ -n "$__wd_detail" ] || __wd_detail="exit $__wd_rc"
printf "%s\t%s\t%s\n" "$__wd_rc" "$(date +%s)" "$(printf "%s" "$__wd_detail" | sed -E "s/(access_token=|refresh_token=|client_secret=|api_key=|Bearer )[A-Za-z0-9._-]{6,}/\1***REDACTED***/g" )" >> "$STATUS"
rm -f "$WD_ERR"

