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
    r2 = await client.post(
        "/api/v1/auth/verify-code", json={"email": email, "code": otp}
    )
    r2.raise_for_status()
    data = r2.json()["data"]
    t2 = time.perf_counter()
    print(f"[auth] {email} resend={t1-t0:.3f}s verify={t2-t1:.3f}s")
    return data["access_token"], data["user"]


async def drain_events(ws, timeout=5):
    """Drain all events from WS for `timeout` seconds."""
    deadline = time.perf_counter() + timeout
    events = []
    while time.perf_counter() < deadline:
        remaining = max(0.1, deadline - time.perf_counter())
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        except TimeoutError:
            break
        msg = json.loads(raw)
        events.append(msg)
        print(f"  [drain] {msg.get('type')}")
    return events


async def wait_for(ws, msg_type, timeout=30):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        remaining = max(0.1, deadline - time.perf_counter())
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        except TimeoutError:
            continue
        msg = json.loads(raw)
        if msg.get("type") == msg_type:
            return msg
    raise RuntimeError(f"Timeout waiting for {msg_type}")


async def main():
    base = "http://127.0.0.1:8000"
    ws_base = "ws://127.0.0.1:8000"

    async with (
        httpx.AsyncClient(base_url=base, timeout=120.0) as sc,
        httpx.AsyncClient(base_url=base, timeout=120.0) as rc,
    ):
        # Health
        t0 = time.perf_counter()
        await sc.get("/api/health")
        print(f"[setup] health={time.perf_counter()-t0:.3f}s")

        # Login both users
        t0 = time.perf_counter()
        s_token, s_user = await login(sc, "user@example.com")
        await asyncio.sleep(2)  # avoid rate limit
        r_token, r_user = await login(rc, "znwajei@gmail.com")
        print(f"[setup] total login={time.perf_counter()-t0:.3f}s")

        # --- Open BOTH WebSockets first ---
        print("\n--- Phase 1: Connect both WebSockets ---")
        t0 = time.perf_counter()
        async with (
            websockets.connect(
                f"{ws_base}/api/v1/events/ws?token={r_token}",
                ping_interval=20,
                ping_timeout=20,
            ) as rws,
            websockets.connect(
                f"{ws_base}/api/v1/events/ws?token={s_token}",
                ping_interval=20,
                ping_timeout=20,
            ) as sws,
        ):
            print(f"[ws] both connected in {time.perf_counter()-t0:.3f}s")

            # Drain bootstrap events from both (don't block on snapshot)
            print("\n--- Phase 2: Drain bootstrap events ---")
            t0 = time.perf_counter()
            r_events = await drain_events(rws, timeout=8)
            s_events = await drain_events(sws, timeout=8)
            print(f"[ws] bootstrap drain={time.perf_counter()-t0:.3f}s")
            print(
                f"[ws] recipient got {len(r_events)} events, sender got {len(s_events)} events"
            )

            # --- Phase 3: Measure chat latency ---
            print("\n--- Phase 3: Chat round-trip ---")
            client_id = f"test-{int(time.perf_counter()*1000)}"

            t0 = time.perf_counter()
            await sws.send(
                json.dumps(
                    {
                        "type": "chat.send",
                        "recipient_id": r_user["id"],
                        "body": "latency test",
                        "client_id": client_id,
                    }
                )
            )
            print("[chat] sent at t=0")

            t1 = time.perf_counter()
            await wait_for(sws, "chat.send.ack", 30)
            print(f"[timing] send_ack={t1-t0:.3f}s")

            t2 = time.perf_counter()
            await wait_for(sws, "chat.sent", 30)
            print(f"[timing] chat.sent={t2-t1:.3f}s  total_sender={t2-t0:.3f}s")

            t3 = time.perf_counter()
            await wait_for(rws, "chat.message", 30)
            print(f"[timing] recipient_delivery={t3-t2:.3f}s  total_e2e={t3-t0:.3f}s")

            print("\n[SUMMARY]")
            print(f"  send → ack:       {t1-t0:.3f}s")
            print(f"  ack → sent:       {t2-t1:.3f}s")
            print(f"  sent → recipient: {t3-t2:.3f}s")
            print(f"  total e2e:        {t3-t0:.3f}s")
            print("  ✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())
