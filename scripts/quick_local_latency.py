from __future__ import annotations

import asyncio
import json
import time

import httpx
import websockets


async def login(client, email):
    t0 = time.perf_counter()
    r = await client.post("/api/v1/auth/resend-otp", json={"email": email})
    r.raise_for_status()
    otp = r.json()["data"]["otp"]
    t1 = time.perf_counter()
    r2 = await client.post("/api/v1/auth/verify-code", json={"email": email, "code": otp})
    r2.raise_for_status()
    data = r2.json()["data"]
    t2 = time.perf_counter()
    print(f"[auth] {email} resend={t1-t0:.3f}s verify={t2-t1:.3f}s")
    return data["access_token"], data["user"]


async def wait_for(ws, msg_type, timeout=30):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        remaining = max(0.01, deadline - time.perf_counter())
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        except TimeoutError:
            continue
        msg = json.loads(raw)
        if msg.get("type") == msg_type:
            return msg, time.perf_counter()
    raise RuntimeError(f"Timeout waiting for {msg_type}")


async def main():
    base = "http://127.0.0.1:8000"
    ws_base = "ws://127.0.0.1:8000"

    async with httpx.AsyncClient(base_url=base, timeout=120.0) as sc, \
               httpx.AsyncClient(base_url=base, timeout=120.0) as rc:
        await sc.get("/api/health")

        t0 = time.perf_counter()
        s_token, s_user = await login(sc, "user@example.com")
        await asyncio.sleep(2)
        r_token, r_user = await login(rc, "znwajei@gmail.com")
        print(f"[setup] login={time.perf_counter()-t0:.3f}s")

        async with websockets.connect(f"{ws_base}/api/v1/events/ws?token={r_token}", ping_interval=20, ping_timeout=20) as rws, \
                   websockets.connect(f"{ws_base}/api/v1/events/ws?token={s_token}", ping_interval=20, ping_timeout=20) as sws:

            # Drain bootstrap
            for label, ws in [("R", rws), ("S", sws)]:
                deadline = time.perf_counter() + 8
                while time.perf_counter() < deadline:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=max(0.1, deadline - time.perf_counter()))
                    except TimeoutError:
                        break
                    msg = json.loads(raw)

            # CHAT ROUND-TRIP
            t0 = time.perf_counter()
            client_id = f"test-{int(time.perf_counter()*1000)}"
            await sws.send(json.dumps({
                "type": "chat.send",
                "recipient_id": r_user["id"],
                "body": "latency test",
                "client_id": client_id,
            }))

            ack, t1 = await wait_for(sws, "chat.send.ack", 30)
            print(f"[timing] send_ack={t1-t0:.3f}s")

            sent, t2 = await wait_for(sws, "chat.sent", 30)
            print(f"[timing] chat.sent={t2-t1:.3f}s")

            msg, t3 = await wait_for(rws, "chat.message", 30)
            print(f"[timing] recipient_delivery={t3-t2:.3f}s  total_e2e={t3-t0:.3f}s")
            print(f"\n✅ send→ack={t1-t0:.3f}s  ack→sent={t2-t1:.3f}s  sent→recipient={t3-t2:.3f}s  TOTAL={t3-t0:.3f}s")


if __name__ == "__main__":
    asyncio.run(main())
