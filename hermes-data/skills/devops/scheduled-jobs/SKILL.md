---
name: scheduled-jobs
description: "Manage Hermes cron jobs and script-backed scheduled tasks safely, including no_agent watchdog patterns and calendar-edge schedules."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Hermes, Cron, Scheduling, Automation]
---

# Scheduled Jobs

Use this skill when creating, updating, debugging, or verifying Hermes `cronjob` tasks, especially script-backed jobs (`no_agent=true`) and schedules with calendar logic.

## Core workflow

1. **List before changing**
   - Always call `cronjob(action='list')` before update/pause/remove/run.
   - Never guess job IDs; use the listed `job_id`.

2. **Preserve delivery and execution mode**
   - When updating schedule only, do not alter `deliver`, `script`, `no_agent`, `skills`, or model settings unless the user asks.
   - For script-only jobs, keep `no_agent=true` so stdout is delivered verbatim and empty stdout stays silent.

3. **Verify after update**
   - Confirm the updated schedule and `next_run_at` from the tool result.
   - If there is a backing script, run a syntax check or safe dry-run where possible.

## Calendar-edge schedules

Hermes cron accepts standard five-field cron expressions like `0 9 * * *`; it may reject extended cron syntax such as `L` for “last day of month”.

### Last calendar day of month pattern

Use a broad cron window plus script-side gating:

- Schedule: `30 20 28-31 * *`
- Script logic: return without printing unless tomorrow is in a different month.

Python gate:

```python
from datetime import date, timedelta

def is_last_calendar_day():
    today = date.today()
    return (today + timedelta(days=1)).month != today.month

if not is_last_calendar_day():
    return  # for no_agent jobs: stay silent, no delivery
```

For `no_agent=true` jobs, empty stdout means no message is delivered. This is the preferred way to avoid noisy “skip” notifications.

### Last trading day vs last calendar day

Clarify which one the user wants:

- Last trading day: usually a weekday/month-end market concept; script may need holiday logic.
- Last calendar day: actual final date of month, even weekend/holiday.

If the user says “只要在每个月最后一天运行”, interpret as last calendar day unless they mention trading days.

## Pitfalls

- Do not use `L` in the cron field unless verified supported by the current Hermes scheduler.
- Do not print “skip” messages from a `no_agent` script if the user expects silence; any non-empty stdout will be delivered.
- Do not replace a precise script-side condition with a broad cron-only schedule if that would send extra messages.
