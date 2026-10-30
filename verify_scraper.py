#!/usr/bin/env python3
"""
verify_scraper.py

Compares scraped courses_data.json against courses.csv ground truth.
Reports prerequisite extraction accuracy by subject and overall.

KEY FIX: Filters out ACTIVE = 'N' courses from the benchmark so that
inactive/retired courses do not count against scraper accuracy.
"""

import json
import re
import pandas as pd

COURSE_CODE_RE = re.compile(r'\b([A-Z]{2,5})[- ](\d{3,4}[A-Z0-9]*)\b')


def normalize_code(prefix, number):
    return f"{prefix.upper().strip()} {number.upper().strip()}"


# ---------------------------------------------------------------------------
# 1. Load Ground Truth from courses.csv — ACTIVE courses only
# ---------------------------------------------------------------------------

df_all    = pd.read_csv('courses.csv')
df        = df_all[df_all['ACTIVE'] == 'Y'].copy()
n_inactive = len(df_all) - len(df)

print(f"\n  Loaded benchmark: {len(df)} ACTIVE courses  "
      f"(filtered out {n_inactive} inactive courses)")

benchmark = {}
for _, row in df.iterrows():
    code = normalize_code(str(row['SUBJECT_CODE']), str(row['COURSE_NUMBER']))
    raw  = row['PREREQUISITES']
    prereqs = set()
    if pd.notna(raw) and str(raw).strip() not in ['NaN', '-', '']:
        for m in COURSE_CODE_RE.findall(str(raw)):
            norm = normalize_code(m[0], m[1])
            if norm != code:
                prereqs.add(norm)
    benchmark[code] = sorted(list(prereqs))


# ---------------------------------------------------------------------------
# 2. Load Scraped Output from courses_data.json
# ---------------------------------------------------------------------------

with open('courses_data.json', 'r') as f:
    scraped_list = json.load(f)

scraped = {}
for c in scraped_list:
    scraped[c['code']] = set(c.get('prerequisite_codes', []))


# ---------------------------------------------------------------------------
# 3. Compare & Report
# ---------------------------------------------------------------------------

print(f"\n{'='*65}")
print(f"{'📊 PREREQUISITE SCRAPING VERIFICATION REPORT':^65}")
print(f"{'='*65}")

total_expected  = 0
total_captured  = 0
total_missed    = 0
total_extra     = 0
subject_results = {}

for code, expected_prereqs in benchmark.items():
    if not expected_prereqs:
        continue

    subject         = code.split()[0]
    scraped_prereqs = scraped.get(code, set())
    expected_set    = set(expected_prereqs)

    captured = expected_set & scraped_prereqs
    missed   = expected_set - scraped_prereqs
    extra    = scraped_prereqs - expected_set

    total_expected += len(expected_set)
    total_captured += len(captured)
    total_missed   += len(missed)
    total_extra    += len(extra)

    if subject not in subject_results:
        subject_results[subject] = {'expected': 0, 'captured': 0, 'missed': 0}
    subject_results[subject]['expected'] += len(expected_set)
    subject_results[subject]['captured'] += len(captured)
    subject_results[subject]['missed']   += len(missed)

# Overall Summary
accuracy = (total_captured / total_expected * 100) if total_expected else 0

print(f"\n  {'Benchmark prereq links (ACTIVE courses only):':<42} {total_expected:>5}")
print(f"  {'Captured by scraper:':<42} {total_captured:>5}")
print(f"  {'Missed by scraper:':<42} {total_missed:>5}")
print(f"  {'Extra (not in benchmark):':<42} {total_extra:>5}")
print(f"\n  {'Overall Accuracy:':<42} {accuracy:>5.1f}%")

if accuracy >= 99:
    print(f"\n  🟢 EXCELLENT — Ready to apply to other catalog years!")
elif accuracy >= 95:
    print(f"\n  🟢 GREAT — Minor edge cases remain. Safe to expand to other years.")
elif accuracy >= 90:
    print(f"\n  🟡 GOOD — Minor tuning needed before expanding to other years.")
elif accuracy >= 75:
    print(f"\n  🟠 FAIR — Significant gaps remain. Review missed subjects below.")
else:
    print(f"\n  🔴 POOR — Scraper needs major fixes before expanding.")

# By Subject
print(f"\n{'─'*65}")
print(f"  {'Subject':<8} {'Expected':>9} {'Captured':>9} {'Missed':>7} {'Accuracy':>9}")
print(f"{'─'*65}")

for subj, stats in sorted(subject_results.items(), key=lambda x: -x[1]['expected']):
    acc  = (stats['captured'] / stats['expected'] * 100) if stats['expected'] else 0
    flag = "✅" if acc >= 90 else ("⚠️ " if acc >= 70 else "❌")
    print(f"  {flag} {subj:<6} {stats['expected']:>9} {stats['captured']:>9} "
          f"{stats['missed']:>7} {acc:>8.1f}%")

print(f"{'='*65}\n")
