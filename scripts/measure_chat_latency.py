from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import dataclass

import httpx
import websockets


@dataclass
class LoginResult:
    access_token: str
    user: dict
    email: str


async def _login_with_resend(client: httpx.AsyncClient, email: str) -> LoginResult:
    resend_started = time.perf_counter()
    resend_response = await client.post(
        "/api/v1/auth/resend-otp", json={"email": email}
    )
    resend_response.raise_for_status()
    resend_payload = resend_response.json()
    resend_elapsed = time.perf_counter() - resend_started

    otp = resend_payload["data"]["otp"]
    verify_started = time.perf_counter()
    verify_response = await client.post(
        "/api/v1/auth/verify-code",
        json={"email": email, "code": otp},
    )
    verify_response.raise_for_status()
    verify_payload = verify_response.json()["data"]
    verify_elapsed = time.perf_counter() - verify_started

    print(
        f"[auth] {email} resend={resend_elapsed:.3f}s verify={verify_elapsed:.3f}s",
        flush=True,
    )
    return LoginResult(
        access_token=verify_payload["access_token"],
        user=verify_payload["user"],
        email=email,
    )


async def _wait_for_message(
    websocket,
    expected_type: str | set[str],
    timeout_seconds: float,
):
    expected_types = (
        {expected_type} if isinstance(expected_type, str) else set(expected_type)
    )
    deadline = time.perf_counter() + timeout_seconds
    while time.perf_counter() < deadline:
        remaining = max(0.1, deadline - time.perf_counter())
        try:
            raw = await asyncio.wait_for(websocket.recv(), timeout=remaining)
        except TimeoutError:
            continue
        message = json.loads(raw)
        if message.get("type") in expected_types:
            return message
    expected_label = " or ".join(sorted(expected_types))
    raise RuntimeError(f"Did not receive {expected_label} within {timeout_seconds}s")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure staging chat latency from login to live recipient delivery"
    )
    parser.add_argument(
        "--base-url",
        default="https://staging.bouwnce.com",
        help="API base URL, e.g. https://staging.bouwnce.com",
    )
    parser.add_argument(
        "--sender-email",
        default="user@example.com",
        help="Sender email to log in with",
    )
    parser.add_argument(
        "--recipient-email",
        default="znwajei@gmail.com",
        help="Recipient email to log in with",
    )
    parser.add_argument(
        "--message",
        default="latency test message",
        help="Chat message to send",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Overall receive timeout in seconds",
    )
    args = parser.parse_args()

    ws_base_url = args.base_url.replace("http://", "ws://").replace(
        "https://", "wss://"
    )

    async with (
        httpx.AsyncClient(base_url=args.base_url, timeout=30.0) as sender_client,
        httpx.AsyncClient(base_url=args.base_url, timeout=30.0) as recipient_client,
    ):
        print(f"[setup] base_url={args.base_url}", flush=True)
        health_started = time.perf_counter()
        health_response = await sender_client.get("/api/health")
        health_response.raise_for_status()
        print(
            f"[setup] health check={time.perf_counter() - health_started:.3f}s",
            flush=True,
        )

        sender_login_started = time.perf_counter()
        sender_login = await _login_with_resend(sender_client, args.sender_email)
        recipient_login = await _login_with_resend(
            recipient_client, args.recipient_email
        )
        print(
            f"[setup] total login={time.perf_counter() - sender_login_started:.3f}s",
            flush=True,
        )

        sender_ws_url = (
            f"{ws_base_url}/api/v1/events/ws?token={sender_login.access_token}"
        )
        recipient_ws_url = (
            f"{ws_base_url}/api/v1/events/ws?token={recipient_login.access_token}"
        )

        print("[ws] opening recipient websocket", flush=True)
        recipient_connect_started = time.perf_counter()
        async with websockets.connect(
            recipient_ws_url, ping_interval=20, ping_timeout=20
        ) as recipient_ws:
            print(
                f"[ws] recipient websocket open={time.perf_counter() - recipient_connect_started:.3f}s",
                flush=True,
            )

            recipient_bootstrap_started = time.perf_counter()
            while True:
                bootstrap_message = await _wait_for_message(
                    recipient_ws, "user.online.snapshot", args.timeout
                )
                if bootstrap_message:
                    break
            print(
                f"[ws] recipient bootstrap received={time.perf_counter() - recipient_bootstrap_started:.3f}s",
                flush=True,
            )

            print("[ws] opening sender websocket", flush=True)
            sender_connect_started = time.perf_counter()
            async with websockets.connect(
                sender_ws_url, ping_interval=20, ping_timeout=20
            ) as sender_ws:
                print(
                    f"[ws] sender websocket open={time.perf_counter() - sender_connect_started:.3f}s",
                    flush=True,
                )

                client_id = f"latency-{int(time.time() * 1000)}"
                send_started = time.perf_counter()
                await sender_ws.send(
                    json.dumps(
                        {
                            "type": "chat.send",
                            "recipient_id": recipient_login.user["id"],
                            "body": args.message,
                            "client_id": client_id,
                        }
                    )
                )
                print("[chat] chat.send sent", flush=True)

                send_ack_started = time.perf_counter()
                sender_first = await _wait_for_message(
                    sender_ws, {"chat.send.ack", "chat.ack", "chat.sent"}, args.timeout
                )
                send_ack_elapsed = time.perf_counter() - send_ack_started

                sender_sent = sender_first
                sent_elapsed = 0.0
                if sender_first.get("type") != "chat.sent":
                    sent_started = time.perf_counter()
                    sender_sent = await _wait_for_message(
                        sender_ws, "chat.sent", args.timeout
                    )
                    sent_elapsed = time.perf_counter() - sent_started
                total_sender_elapsed = time.perf_counter() - send_started

                recipient_message_started = time.perf_counter()
                recipient_message = await _wait_for_message(
                    recipient_ws, "chat.message", args.timeout
                )
                recipient_message_elapsed = (
                    time.perf_counter() - recipient_message_started
                )
                total_recipient_elapsed = time.perf_counter() - send_started

                print(
                    "[result] send_ack:",
                    json.dumps(sender_first, indent=2),
                    flush=True,
                )
                print(
                    "[result] sender_sent:",
                    json.dumps(sender_sent, indent=2),
                    flush=True,
                )
                print(
                    "[result] recipient_message:",
                    json.dumps(recipient_message, indent=2),
                    flush=True,
                )
                print(
                    f"[timing] send_ack_wait={send_ack_elapsed:.3f}s "
                    f"sent_wait={sent_elapsed:.3f}s "
                    f"total_sender={total_sender_elapsed:.3f}s "
                    f"recipient_wait={recipient_message_elapsed:.3f}s "
                    f"total_recipient={total_recipient_elapsed:.3f}s",
                    flush=True,
                )
                if sender_first.get("type") == "chat.sent":
                    print(
                        "[timing] legacy_sender_mode=true (staging still emits chat.sent as the first sender event)",
                        flush=True,
                    )


if __name__ == "__main__":
    asyncio.run(main())
