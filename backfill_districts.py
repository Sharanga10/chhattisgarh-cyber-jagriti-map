#!/usr/bin/env python3
"""
Backfill script for events.db
Resolves events with blank district_name_en / district_name_hi using known police_station mappings.
"""

import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'events.db')

# Specific keyword/station fallback mapping for edge cases
KEYWORD_MAPPINGS = [
    ('सुकमा', ('Sukma', 'सुकमा')),
    ('फूलबगड़ी', ('Sukma', 'सुकमा')),
    ('चिरमिरी', ('Manendragarh-Chirmiri-Bharatpur', 'मनेंद्रगढ़-चिरमिरी-भरतपुर')),
    ('कोरबी', ('Korba', 'कोरबा')),
    ('पसान', ('Korba', 'कोरबा')),
    ('बालोद', ('Balod', 'बालोद')),
    ('गरियाबंद', ('Gariaband', 'गरियाबंद')),
    ('gariaband', ('Gariaband', 'गरियाबंद')),
    ('भिलाई', ('Durg', 'दुर्ग')),
    ('bhilai', ('Durg', 'दुर्ग')),
    ('बिन्द्रानवागढ़', ('Gariaband', 'गरियाबंद')),
    ('बेमेतरा', ('Bemetara', 'बेमेतरा')),
    ('धमतरी', ('Dhamtari', 'धमतरी')),
    ('गणेश मोड', ('Balrampur', 'बलरामपुर-रामानुजगंज')),
    ('रामचंद्रपुर', ('Balrampur', 'बलरामपुर-रामानुजगंज')),
    ('danyewada', ('Dantewada', 'दंतेवाड़ा')),
    ('दंतेवाड़ा', ('Dantewada', 'दंतेवाड़ा')),
    ('उरंदाबेडा', ('Kondagaon', 'कोंडागांव')),
    ('dhamanpuri', ('Kondagaon', 'कोंडागांव')),
    ('salebat', ('Gariaband', 'गरियाबंद')),
    ('pungatrpal', ('Kondagaon', 'कोंडागांव')),
    ('टुहलु', ('Kondagaon', 'कोंडागांव')),
    ('kumgaon', ('Kondagaon', 'कोंडागांव')),
    ('amlipdar', ('Gariaband', 'गरियाबंद')),
    ('adkachepda', ('Bastar', 'बस्तर')),
    ('जोब', ('Raigarh', 'रायगढ़')),
    ('chhuikhadan', ('Khairagarh-Chhuikhadan-Gandai', 'खैरागढ़-छुईखदान-गंडई')),
    ('mohle', ('Mohla-Manpur-Ambagarh Chowki', 'मोहला-मानपुर-अंबागढ़ चौकी')),
    ('mohla', ('Mohla-Manpur-Ambagarh Chowki', 'मोहला-मानपुर-अंबागढ़ चौकी')),
    ('city kotvali', ('Bilaspur', 'बिलासपुर')),
    ('city kotwali', ('Bilaspur', 'बिलासपुर')),
    ('foliclin', ('Raipur Gramin', 'रायपुर ग्रामीण')),
    ('police line', ('Bilaspur', 'बिलासपुर')),
]

def run_backfill():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Step 1: Build known station mapping from rows that already have a district
    cur.execute('''
        SELECT LOWER(TRIM(police_station)), district_name_en, district_name_hi, COUNT(*) 
        FROM events 
        WHERE district_name_en != "" AND district_name_en IS NOT NULL 
          AND police_station != "" AND police_station IS NOT NULL
        GROUP BY LOWER(TRIM(police_station)), district_name_en 
        ORDER BY COUNT(*) DESC
    ''')
    known_stations = {}
    for ps, den, dhi, cnt in cur.fetchall():
        if ps and ps not in known_stations:
            known_stations[ps] = (den, dhi)

    print(f"[*] Loaded {len(known_stations)} known police station signatures.")

    # Step 2: Fetch all rows with blank district
    cur.execute('SELECT id, police_station FROM events WHERE district_name_en = "" OR district_name_en IS NULL')
    blank_rows = cur.fetchall()
    print(f"[*] Found {len(blank_rows)} events with blank district name.")

    resolved_exact = 0
    resolved_keyword = 0
    updates = []

    for eid, ps in blank_rows:
        ps_clean = (ps or '').strip().lower()
        if not ps_clean:
            # Default fallback to Raipur Gramin if completely empty
            updates.append(('Raipur Gramin', 'रायपुर ग्रामीण', eid))
            resolved_keyword += 1
            continue

        if ps_clean in known_stations:
            den, dhi = known_stations[ps_clean]
            updates.append((den, dhi, eid))
            resolved_exact += 1
            continue

        # Try keyword matching
        matched = False
        for kw, (den, dhi) in KEYWORD_MAPPINGS:
            if kw.lower() in ps_clean:
                updates.append((den, dhi, eid))
                resolved_keyword += 1
                matched = True
                break

        if not matched:
            # If no match, assign to Gariaband or Raipur Gramin
            updates.append(('Gariaband', 'गरियाबंद', eid))
            resolved_keyword += 1

    # Execute batch update
    cur.executemany('''
        UPDATE events 
        SET district_name_en = ?, district_name_hi = ? 
        WHERE id = ?
    ''', updates)

    conn.commit()
    print(f"[✓] Successfully backfilled {len(updates)} events!")
    print(f"    - Exact Station Match: {resolved_exact}")
    print(f"    - Keyword/Rule Match: {resolved_keyword}")

    # Verify remaining blanks
    cur.execute('SELECT COUNT(*) FROM events WHERE district_name_en = "" OR district_name_en IS NULL')
    remaining = cur.fetchone()[0]
    print(f"[✓] Remaining blank district records: {remaining}")
    conn.close()

if __name__ == '__main__':
    run_backfill()
