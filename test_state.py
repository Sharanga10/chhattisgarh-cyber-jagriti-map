import os
import json
from datetime import datetime, timedelta

STATE_FILE = os.path.join(BASE_DIR, 'reports', 'last_run.json')

def should_run(now=None):
    if now is None:
        now = datetime.now()
    
    # The operational day cutoff is 21:00 (9 PM).
    # If it's before 21:00, the last completed reporting cycle should be yesterday's date.
    # If it's at or after 21:00, the current reporting cycle is today's date.
    if now.hour < 21:
        target_cycle_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        target_cycle_date = now.strftime("%Y-%m-%d")

    if not os.path.exists(STATE_FILE):
        return True, target_cycle_date, "No previous run recorded"

    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        last_date = state.get("last_success_date")
        if last_date != target_cycle_date:
            return True, target_cycle_date, f"Missed cycle: last was {last_date}, target is {target_cycle_date}"
        return False, target_cycle_date, f"Already completed for cycle {target_cycle_date}"
    except Exception as e:
        return True, target_cycle_date, f"State file error: {e}"

print("Test now:", should_run())
print("Test at 21:05:", should_run(datetime(2026, 9, 6, 21, 5)))
print("Test next day at 08:30 morning:", should_run(datetime(2026, 9, 7, 8, 30)))
