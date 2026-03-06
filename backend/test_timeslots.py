"""Quick smoke-test for the timeslot CRUD API."""
import requests, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = "http://localhost:8000"

# Signup (public self-registration for first-time setup)
reg = requests.post(f"{BASE}/auth/signup", json={
    "email": "admin@cvmu.edu.in", "password": "admin123",
    "full_name": "Admin", "role": "super_admin",
    "college_name": "CVM University"
})
print(f"Signup: {reg.status_code}")
if reg.status_code == 200:
    token = reg.json()["access_token"]
elif reg.status_code == 409:
    # Already registered, login instead
    resp = requests.post(f"{BASE}/auth/login", json={"email": "admin@cvmu.edu.in", "password": "admin123"})
    print(f"Login: {resp.status_code}")
    if resp.status_code != 200:
        print("Login failed:", resp.text)
        exit(1)
    token = resp.json()["access_token"]
else:
    print("Signup failed:", reg.text)
    exit(1)
h = {"Authorization": f"Bearer {token}"}

# 0. Delete all existing slots first for idempotent test
existing = requests.get(f"{BASE}/timeslots", headers=h).json()
for s in existing:
    requests.delete(f"{BASE}/timeslots/{s['slot_id']}", headers=h)
print(f"0. Cleaned {len(existing)} existing slots")

# 1. Seed defaults
r = requests.post(f"{BASE}/timeslots/seed-defaults", headers=h)
print(f"1. Seed: {r.status_code} -> {len(r.json())} slots")

# 2. List
r = requests.get(f"{BASE}/timeslots", headers=h)
slots = r.json()
print(f"2. List: {r.status_code} -> {len(slots)} slots")
for s in slots:
    print(f"   #{s['slot_order']} {s['label']} ({s['slot_type']}) {s['start_time']}-{s['end_time']}")

# 3. Update first slot label
sid = slots[0]["slot_id"]
r = requests.put(f"{BASE}/timeslots/{sid}", headers=h, json={"label": "Morning 1"})
print(f"3. Update: {r.status_code} -> label={r.json()['label']}")

# 4. Create a new slot
r = requests.post(f"{BASE}/timeslots", headers=h, json={
    "label": "Extra Lab", "start_time": "19:00", "end_time": "21:00",
    "slot_type": "lab", "slot_order": 9
})
print(f"4. Create: {r.status_code} -> {r.json()['label']}")
new_id = r.json()["slot_id"]

# 5. Delete the new slot
r = requests.delete(f"{BASE}/timeslots/{new_id}", headers=h)
print(f"5. Delete: {r.status_code}")

# 6. Reorder: swap slots 1 and 2
ids = [s["slot_id"] for s in slots]
ids[0], ids[1] = ids[1], ids[0]
r = requests.put(f"{BASE}/timeslots/reorder/bulk", headers=h, json={"slot_ids": ids})
reordered = r.json()
print(f"6. Reorder: {r.status_code} -> first={reordered[0]['label']}, second={reordered[1]['label']}")

# 7. Seed again should 409
r = requests.post(f"{BASE}/timeslots/seed-defaults", headers=h)
print(f"7. Seed again: {r.status_code} (expect 409)")

print("\nAll timeslot API tests passed!")
