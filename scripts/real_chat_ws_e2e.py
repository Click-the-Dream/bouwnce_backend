from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import socket
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import uvicorn
import websockets

import app.service.auth_service as auth_module
from app.db.redis import close_redis_client
from main import app


@dataclass
class LoginResult:
    access_token: str
    user: dict
    email: str


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


async def _login_with_resend(client: httpx.AsyncClient, email: str) -> LoginResult:
    print(f"[auth] resend otp for {email}", flush=True)
    resend_response = await client.post(
        "/api/v1/auth/resend-otp", json={"email": email}
    )
    resend_response.raise_for_status()
    otp = resend_response.json()["data"]["otp"]
    print(f"[auth] otp for {email}: {otp}", flush=True)

    verify_response = await client.post(
        "/api/v1/auth/verify-code",
        json={"email": email, "code": otp},
    )
    verify_response.raise_for_status()
    verify_payload = verify_response.json()["data"]
    print(f"[auth] verified {email}", flush=True)
    return LoginResult(
        access_token=verify_payload["access_token"],
        user=verify_payload["user"],
        email=email,
    )


async def _read_until_chat_message(websocket, label: str) -> tuple[list[dict], dict]:
    messages: list[dict] = []
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            raw = await asyncio.wait_for(websocket.recv(), timeout=2)
        except TimeoutError:
            continue

        message = json.loads(raw)
        messages.append(message)
        print(f"[{label}] {message}", flush=True)
        if message.get("type") == "chat.message":
            return messages, message

    raise RuntimeError(f"{label} did not receive chat.message")


async def _wait_for_health(client: httpx.AsyncClient) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            response = await client.get("/api/health")
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            continue
        await asyncio.sleep(0.2)
    raise RuntimeError("Local app never became healthy")


async def main(base_url: str | None = None) -> None:
    original_send_email = auth_module.send_email

    def _noop_send_email(*args, **kwargs):
        return None

    auth_module.send_email = _noop_send_email
    server = None
    server_thread = None

    try:
        if base_url is None:
            port = _find_free_port()
            base_url = f"http://127.0.0.1:{port}"
            ws_base_url = f"ws://127.0.0.1:{port}"
            print(f"[setup] starting local app on 127.0.0.1:{port}", flush=True)
            server = uvicorn.Server(
                uvicorn.Config(
                    app,
                    host="127.0.0.1",
                    port=port,
                    log_level="warning",
                    lifespan="on",
                    access_log=False,
                )
            )
            server_thread = threading.Thread(target=server.run, daemon=True)
            server_thread.start()
        else:
            ws_base_url = base_url.replace("http://", "ws://").replace(
                "https://", "wss://"
            )
            print(f"[setup] using existing app at {base_url}", flush=True)

        async with (
            httpx.AsyncClient(base_url=base_url, timeout=30.0) as sender_client,
            httpx.AsyncClient(base_url=base_url, timeout=30.0) as recipient_client,
        ):
            await _wait_for_health(sender_client)
            print("[setup] health check passed", flush=True)
            sender_email = "user@example.com"
            recipient_email = "znwajei@gmail.com"

            sender_login = await _login_with_resend(sender_client, sender_email)
            recipient_login = await _login_with_resend(
                recipient_client, recipient_email
            )
            print("[setup] both users logged in", flush=True)

            sender_ws_url = (
                f"{ws_base_url}/api/v1/events/ws?token={sender_login.access_token}"
            )
            recipient_ws_url = (
                f"{ws_base_url}/api/v1/events/ws?token={recipient_login.access_token}"
            )

            print("[ws] opening recipient websocket", flush=True)
            async with websockets.connect(
                recipient_ws_url, ping_interval=20, ping_timeout=20
            ) as recipient_ws:
                print("[ws] recipient websocket open", flush=True)
                recipient_reader = asyncio.create_task(
                    _read_until_chat_message(recipient_ws, "recipient")
                )

                await asyncio.sleep(0.25)

                print("[ws] opening sender websocket", flush=True)
                async with websockets.connect(
                    sender_ws_url, ping_interval=20, ping_timeout=20
                ) as sender_ws:
                    print("[ws] sender websocket open", flush=True)
                    client_id = f"temp-{uuid.uuid4().hex}"
                    await sender_ws.send(
                        json.dumps(
                            {
                                "type": "chat.send",
                                "recipient_id": recipient_login.user["id"],
                                "body": "hello from real login test",
                                "client_id": client_id,
                            }
                        )
                    )
                    print("[ws] sender sent chat.send", flush=True)

                    sender_messages: list[dict] = []
                    sender_deadline = time.monotonic() + 20
                    sender_ack = None
                    while time.monotonic() < sender_deadline:
                        try:
                            raw = await asyncio.wait_for(sender_ws.recv(), timeout=2)
                        except asyncio.TimeoutError:
                            continue
                        message = json.loads(raw)
                        sender_messages.append(message)
                        print(f"[sender] {message}", flush=True)
                        if message.get("type") == "chat.sent":
                            sender_ack = message
                            break

                    if sender_ack is None:
                        raise RuntimeError("Sender did not receive chat.sent")

                    recipient_messages, recipient_chat_message = await recipient_reader
                    print("RESULT: sender ack and recipient live message received")

    finally:
        auth_module.send_email = original_send_email
        if server is not None:
            server.should_exit = True
        if server_thread is not None:
            server_thread.join(timeout=5)
        with contextlib.suppress(Exception):
            await close_redis_client()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real chat websocket end-to-end test")
    parser.add_argument(
        "--base-url",
        default=None,
        help="Use an already running API server, e.g. http://127.0.0.1:8000",
    )
    args = parser.parse_args()
    asyncio.run(main(base_url=args.base_url))
