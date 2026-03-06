import asyncio, json, httpx

async def test():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        login = await client.post("/auth/login", json={"email": "hod.cp@cvmu.edu.in", "password": "hod123"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Test 1: Free slots overview
        r1 = await client.post("/chat/message", json={"message": "Which slots are free for sem 7?"}, headers=headers)
        d = r1.json()
        print("=== Test 1: Free slots overview ===")
        print(f"Intent: {d.get('intent')} | Confidence: {d.get('confidence')}")
        print(d["reply"][:800])
        print()

        # Test 2: Specific day+period
        r2 = await client.post("/chat/message", json={"message": "Which rooms are free Tuesday P3 for sem 7?"}, headers=headers)
        d2 = r2.json()
        print("=== Test 2: Free rooms Tuesday P3 ===")
        print(f"Intent: {d2.get('intent')} | Confidence: {d2.get('confidence')}")
        print(d2["reply"][:800])
        print()

        # Test 3: Reschedule intent
        r3 = await client.post("/chat/message", json={"message": "Add extra lecture for sem 7 on Tuesday P2"}, headers=headers)
        d3 = r3.json()
        print("=== Test 3: Reschedule ===")
        print(f"Intent: {d3.get('intent')} | Confidence: {d3.get('confidence')}")
        print(d3["reply"][:800])

asyncio.run(test())
