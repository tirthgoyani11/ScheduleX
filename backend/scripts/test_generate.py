"""Quick script to trigger timetable generation and verify 2-hour contiguous labs."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from urllib.request import Request, urlopen

BASE = "http://localhost:8000"

def api(method, path, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    req = Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    resp = urlopen(req)
    return json.loads(resp.read())

# Login
login = api("POST", "/auth/login", {"email": "admin@cvmu.edu.in", "password": "admin123"})
token = login["access_token"]
dept_id = login["dept_id"]

# Get subjects & faculty
subs = api("GET", "/subjects/", token=token)
facs = api("GET", "/faculty/", token=token)

# Build faculty_subject_map by expertise matching
sub_by_code = {s["subject_code"]: s for s in subs}
fac_by_emp = {f["employee_id"]: f for f in facs}

# Explicit assignment: each lab subject gets a unique faculty
# FAC001 (CN,OS) → CS301(CN); FAC005 (OS,DAA) → CS302(OS);
# FAC002 (DBMS,SE) → CS303(DBMS), CS304(SE); FAC004 (WP) → CS307(WP);
# FAC003 (DAA,TOC) → CS305(DAA), CS306(TOC)
assignment = {
    "FAC001": ["CS301"],
    "FAC005": ["CS302"],
    "FAC002": ["CS303", "CS304"],
    "FAC003": ["CS305", "CS306"],
    "FAC004": ["CS307"],
}

final_map = {}
for emp_id, codes in assignment.items():
    fac = fac_by_emp.get(emp_id)
    if not fac:
        continue
    sids = []
    for c in codes:
        s = sub_by_code.get(c)
        if s:
            sids.append(s["subject_id"])
    if sids:
        final_map[fac["faculty_id"]] = sids

print(f"Faculty-Subject Map: {len(final_map)} faculty → {sum(len(v) for v in final_map.values())} assignments")

# Generate timetable
gen_body = {
    "dept_id": dept_id,
    "semester": 5,
    "academic_year": "2025-26",
    "faculty_subject_map": final_map,
    "time_limit_seconds": 120,
}

print("Generating timetable...")
result = api("POST", "/timetable/generate", gen_body, token=token)
print(f"Status: {result['status']}, Score: {result.get('score')}, Entries: {result.get('entry_count')}")

if result["status"] in ("OPTIMAL", "FEASIBLE"):
    # Get entries
    tt_id = result.get("timetable_id")
    if not tt_id:
        tts = api("GET", "/timetable/", token=token)
        tt_id = tts[0]["timetable_id"]
    
    tt = api("GET", f"/timetable/{tt_id}", token=token)
    entries = tt["entries"]
    
    # Analyze lab entries
    lab_entries = [e for e in entries if e["batch"] is not None]
    theory_entries = [e for e in entries if e["batch"] is None]
    print(f"\nTheory entries: {len(theory_entries)}, Lab entries: {len(lab_entries)}")
    
    # Check contiguity AND same-room: group lab entries by (subject, batch, day)
    from collections import defaultdict
    lab_groups = defaultdict(list)
    for e in lab_entries:
        key = (e["subject_name"], e["batch"], e["day"])
        lab_groups[key].append(e)
    
    print("\nLab blocks (should be 2 consecutive periods, SAME room):")
    all_ok = True
    for (subj, batch, day), ents in sorted(lab_groups.items()):
        ents.sort(key=lambda x: x["period"])
        periods = [e["period"] for e in ents]
        rooms = [e["room_name"] for e in ents]
        contiguous = len(periods) == 2 and periods[1] == periods[0] + 1
        same_room = len(set(rooms)) == 1
        status = "OK" if (contiguous and same_room) else "FAIL"
        if not (contiguous and same_room):
            all_ok = False
        print(f"  {subj} Batch-{batch} {day}: periods {periods} rooms {rooms} [{status}]")
    
    print(f"\n{'ALL LABS CONTIGUOUS + SAME ROOM' if all_ok else 'SOME LABS HAVE ISSUES!'}")
else:
    print("Diagnosis:", result.get("diagnosis"))
