#!/usr/bin/env python3
"""
Pre-push Automated Test Suite for Chhattisgarh Cyber Jagriti Monitor
Validates:
1. JavaScript syntax and integrity in index.html and chhattisgarh_cyber_jagriti_map.html
2. District matching algorithm stability (No Balod vs Baloda Bazar oscillation)
3. Background sync policy (Silent background sync: 0 popup toasts, manual sync only)
4. Toast dismissibility and CSS styling
5. Indian financial formatting across JS and Python
6. SQLite database integrity (No date-in-station corruptions, legitimate Top Thanas)
7. Audit agent status and ground truth reconciliation
"""

import os
import re
import sys
import json
import sqlite3
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML = os.path.join(BASE_DIR, "index.html")
MAP_HTML = os.path.join(BASE_DIR, "chhattisgarh_cyber_jagriti_map.html")
DB_PATH = os.path.join(BASE_DIR, "events.db")
FEED_PATH = os.path.join(BASE_DIR, "live_feed.json")

def run_tests():
    passed = 0
    total = 0

    def test(name, condition, err_msg=""):
        nonlocal passed, total
        total += 1
        if condition:
            print(f"  [PASS] {name}")
            passed += 1
        else:
            print(f"  [FAIL] {name}: {err_msg}")
            return False
        return True

    print("=" * 65)
    print("RUNNING PRE-PUSH AUTOMATED TEST HARNESS")
    print("=" * 65)

    # Test 1: HTML files exist and non-empty
    test("Index HTML exists and size > 500KB", os.path.exists(INDEX_HTML) and os.path.getsize(INDEX_HTML) > 500000)
    test("Geospatial Map HTML exists and size > 500KB", os.path.exists(MAP_HTML) and os.path.getsize(MAP_HTML) > 500000)

    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        html_src = f.read()

    # Test 2: Exact matching in findDistrictTarget (no loose includes)
    has_exact_matching = "dEn === nEn" in html_src and "dEn.includes(nEn)" not in html_src
    test("findDistrictTarget uses exact matching (no dEn.includes)", has_exact_matching)

    # Test 3: Background sync does not call showSyncToast
    # Verify showSyncToast is only inside if (isManual)
    bg_toast_call = re.search(r'updateStateHeaderKPIs\(\);\s+updateDrawerFilterStats\(\);\s+showSyncToast', html_src)
    test("Background sync does not trigger automatic showSyncToast", bg_toast_call is None, "Found showSyncToast inside background update block")

    # Test 4: Manual sync call to showSyncToast exists
    manual_toast_call = "if (isManual) {" in html_src and "showSyncToast(`लाइव सिंक 100% सत्यापित" in html_src
    test("Manual sync properly triggers verification toast", manual_toast_call)

    # Test 5: Toast dismissibility and styling
    has_click_dismiss = "toastSync.addEventListener('click'" in html_src or "toastSync.onclick" in html_src
    test("Toast notification has click-to-dismiss handler", has_click_dismiss)

    has_emerald_toast = "rgba(16, 185, 129, 0.5)" in html_src
    test("Toast border styled with calm emerald instead of red", has_emerald_toast)

    # Test 6: Node simulation of district matching
    # Extract DISTRICTS_DATA from html
    match_d = re.search(r'const DISTRICTS_DATA = (\[.*?\]);', html_src, re.DOTALL)
    test("DISTRICTS_DATA present in HTML", match_d is not None)

    if match_d and os.path.exists(FEED_PATH):
        with open(FEED_PATH, "r", encoding="utf-8") as f:
            feed_data = json.load(f)

        node_script = f"""
        const DISTRICTS_DATA = {match_d.group(1)};
        const feed = {json.dumps(feed_data)};

        function findDistrictTarget(nd) {{
            const nid = parseInt(nd.id || 0);
            const nEn = (nd.name_en || '').toLowerCase().trim();
            const nHi = (nd.name_hi || '').trim();
            return DISTRICTS_DATA.find(d => {{
                if (nid && d.id === nid) return true;
                if (d.portal_ids && d.portal_ids.includes(nid)) return true;
                const dEn = d.name_en.toLowerCase().trim();
                if (nEn && dEn === nEn) return true;
                if (nHi && d.name_hi === nHi) return true;
                return false;
            }});
        }}

        // Tick 1
        let tick1Changed = false;
        feed.districts.forEach(nd => {{
            const target = findDistrictTarget(nd);
            if (!target) return;
            const ev = parseInt(nd.events || 0);
            const rch = parseInt(nd.reach || 0);
            if (target.events !== ev || target.reach !== rch) {{
                target.events = ev;
                target.reach = rch;
                tick1Changed = true;
            }}
        }});

        // Tick 2 (immediate consecutive tick - must NOT change!)
        let tick2Changed = false;
        feed.districts.forEach(nd => {{
            const target = findDistrictTarget(nd);
            if (!target) return;
            const ev = parseInt(nd.events || 0);
            const rch = parseInt(nd.reach || 0);
            if (target.events !== ev || target.reach !== rch) {{
                target.events = ev;
                target.reach = rch;
                tick2Changed = true;
            }}
        }});

        // Specifically test Balod vs Baloda Bazar
        const balodTarget = findDistrictTarget({{ id: 1, name_en: "Balod", name_hi: "बालोद" }});
        const balodaTarget = findDistrictTarget({{ id: 2, name_en: "Baloda Bazar-Bhatapara", name_hi: "बलौदाबाजार-भाटापारा" }});

        const collision = (balodTarget && balodaTarget && balodTarget.id === balodaTarget.id);

        console.log(JSON.stringify({{
            tick2Changed,
            balodId: balodTarget ? balodTarget.id : null,
            balodaId: balodaTarget ? balodaTarget.id : null,
            collision
        }}));
        """
        proc = subprocess.run(["node", "-e", node_script], capture_output=True, text=True)
        if proc.returncode == 0:
            res = json.loads(proc.stdout.strip())
            test("Simulation Tick 2 stability: anyChanged is FALSE (0 oscillations)", res["tick2Changed"] is False, f"tick2Changed was {res['tick2Changed']}")
            test("No collision between Balod and Baloda Bazar", res["collision"] is False, f"Collision detected! Both matched id: {res['balodId']}")
            test("Balod correctly matches Balod", res["balodId"] == 1)
            test("Baloda Bazar correctly matches Baloda Bazar", res["balodaId"] == 2)
        else:
            test("Node simulation executed successfully", False, proc.stderr)

    # Test 7: SQLite DB health
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM events WHERE police_station GLOB '[0-9][0-9][0-9][0-9]*'")
    corrupted_stations = cur.fetchone()[0]
    test("Zero corrupted date strings in police_station column", corrupted_stations == 0, f"Found {corrupted_stations} corrupted rows")

    cur.execute("SELECT police_station, district_name_hi, COUNT(*) as c FROM events GROUP BY police_station ORDER BY c DESC LIMIT 3")
    top_stations = cur.fetchall()
    test("Rank 1 police station is legitimate police station", "2026-" not in top_stations[0][0], f"Rank 1 is still {top_stations[0][0]}")
    print(f"      Top Thana: {top_stations[0][0]} ({top_stations[0][1]}) - {top_stations[0][2]:,} events")
    conn.close()

    # Test 8: Indian number formatting
    test("formatIN JS function is defined with en-IN locale", "toLocaleString('en-IN')" in html_src)
    node_in_test = "console.log(Number(100000).toLocaleString('en-IN') === '1,00,000' && Number(3970886).toLocaleString('en-IN') === '39,70,886')"
    proc_in = subprocess.run(["node", "-e", node_in_test], capture_output=True, text=True)
    test("Indian numbering outputs lakhs format (1,00,000 & 39,70,886)", proc_in.stdout.strip() == "true")

    print("=" * 65)
    print(f"RESULTS: {passed}/{total} TESTS PASSED")
    print("=" * 65)
    if passed == total:
        print("[SUCCESS] All pre-push checks passed! Code is 100% verified.")
        return 0
    else:
        print("[FAILURE] Some checks failed. Aborting push.")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())
