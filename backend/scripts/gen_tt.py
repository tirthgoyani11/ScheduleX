"""Generate timetable for CP Sem 1 via API."""
import asyncio, json, httpx

BASE = "http://127.0.0.1:8000"

async def main():
    async with httpx.AsyncClient(timeout=300) as c:
        # Login
        r = await c.post(f"{BASE}/auth/login", json={"email": "hod.cp@cvmu.edu.in", "password": "hod123"})
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        # Get subjects for sem 1
        subs = (await c.get(f"{BASE}/subjects?semester=1", headers=h)).json()
        sids = [s["subject_id"] for s in subs]
        print(f"Subjects ({len(sids)}):")
        for s in subs:
            print(f"  {s['name']} (lec={s['lecture_hours']}, lab={s['lab_hours']})")

        # Get faculty
        fac = (await c.get(f"{BASE}/faculty", headers=h)).json()
        fids = [f["faculty_id"] for f in fac]
        print(f"\nFaculty ({len(fids)}):")
        for f in fac:
            print(f"  {f['name']}")

        # Round-robin map
        fsmap = {}
        for i, fid in enumerate(fids):
            assigned = [sids[j] for j in range(len(sids)) if j % len(fids) == i]
            if assigned:
                fsmap[fid] = assigned
        print(f"\nMap has {len(fsmap)} entries")

        # Generate
        body = {
            "semester": 1,
            "academic_year": "2025-26",
            "faculty_subject_map": fsmap,
            "time_limit_seconds": 120,
        }
        print("\nGenerating timetable...")
        r = await c.post(f"{BASE}/timetable/generate", json=body, headers=h)
        print(f"Status: {r.status_code}")
        print(json.dumps(r.json(), indent=2))

asyncio.run(main())
